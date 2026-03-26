import streamlit as st
import pandas as pd
import braintree
import boto3
import os
import uuid
import requests
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# --- DUAL-MODE SECRET LOADER ---
# Reads from Streamlit Cloud secrets.toml in production,
# falls back to local .env file for development.
load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

# Initialize Supabase
url = get_secret("SUPABASE_URL")
key = get_secret("SUPABASE_KEY")
if url and key:
    supabase: Client = create_client(url, key)
else:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY in secrets.")
    st.stop()

# Initialize S3 via Boto3
s3_client = boto3.client(
    's3',
    aws_access_key_id=get_secret("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=get_secret("AWS_SECRET_ACCESS_KEY"),
    endpoint_url=f"{get_secret('SUPABASE_URL')}/storage/v1/s3",
    region_name="us-east-1"
)
S3_BUCKET = "thriftstar"

# Initialize Braintree Gateway
try:
    gateway = braintree.BraintreeGateway(
        braintree.Configuration(
            environment=braintree.Environment.Sandbox,
            merchant_id=get_secret("BRAINTREE_MERCHANT_ID"),
            public_key=get_secret("BRAINTREE_PUBLIC_KEY"),
            private_key=get_secret("BRAINTREE_PRIVATE_KEY")
        )
    )
    braintree_configured = True
except Exception as e:
    braintree_configured = False

# Initialize Shippo
SHIPPO_API_KEY = get_secret("SHIPPO_API_KEY")
shippo_configured = bool(SHIPPO_API_KEY)

# Set page config
st.set_page_config(page_title="Thrift Star", layout="wide", page_icon="⭐")

# --- PERSISTENT AUTHENTICATION ENGINE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'refresh_token' not in st.session_state:
    st.session_state.refresh_token = None
if 'checkout_item' not in st.session_state:
    st.session_state.checkout_item = None
if 'view_item' not in st.session_state:
    st.session_state.view_item = None

SESSION_FILE = "auth_cookies.json"

def get_persisted_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_session(device_id, access, refresh):
    sessions = get_persisted_sessions()
    sessions[device_id] = {"access_token": access, "refresh_token": refresh}
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f)

def remove_session(device_id):
    sessions = get_persisted_sessions()
    if device_id in sessions:
        del sessions[device_id]
        with open(SESSION_FILE, "w") as f:
            json.dump(sessions, f)

device_id = st.query_params.get("device")

# Attempt Hard-Reload Recovery
if device_id and st.session_state.user is None:
    sessions = get_persisted_sessions()
    if device_id in sessions:
        tokens = sessions[device_id]
        try:
            res = supabase.auth.set_session(tokens["access_token"], tokens["refresh_token"])
            if res.user:
                st.session_state.user = res.user
                st.session_state.access_token = tokens["access_token"]
                st.session_state.refresh_token = tokens["refresh_token"]
        except Exception:
            remove_session(device_id)

# General Streamlit Rerun Recovery
if st.session_state.user is not None and st.session_state.access_token is not None:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except Exception:
        pass

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    
    did = st.query_params.get("device")
    if did:
        remove_session(did)
        st.query_params.clear()
        
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.checkout_item = None
    st.session_state.view_item = None

# --- DATABASE / API HELPERS ---
def get_user_by_id(user_id):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def process_sandbox_payment(amount):
    if not braintree_configured:
        return False, "Braintree gateway not configured. Check your .env file."
    
    result = gateway.transaction.sale({
        "amount": f"{amount:.2f}",
        "payment_method_nonce": "fake-valid-nonce",
        "options": {"submit_for_settlement": True}
    })
    return (True, result.transaction.id) if result.is_success else (False, result.message)

def create_shipping_label(sender_id, receiver_id):
    if not shippo_configured:
        return False, "Shippo API key not configured (Restart Streamlit Server!)"
        
    # Get Real Profiles
    sender = get_user_by_id(sender_id)
    receiver = get_user_by_id(receiver_id)
    
    addr_from = sender.get('address')
    addr_to = receiver.get('address')
    
    if not addr_from or not addr_from.get('street1'):
        return False, f"Missing Sender Address: {sender['username']} must update their Profile Settings."
    if not addr_to or not addr_to.get('street1'):
        return False, f"Missing Receiver Address: {receiver['username']} must update their Profile Settings."

    # USPS forces us to provide email and phone. We inject them dynamically.
    addr_from["email"] = sender.get("email", "support@thriftstar.app")
    if not addr_from.get("phone"):
        addr_from["phone"] = "5555555555"
        
    addr_to["email"] = receiver.get("email", "support@thriftstar.app")
    if not addr_to.get("phone"):
        addr_to["phone"] = "5555555555"

    url = "https://api.goshippo.com/shipments/"
    headers = {
        "Authorization": f"ShippoToken {SHIPPO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "address_from": addr_from,
        "address_to": addr_to,
        "parcels": [{
            "length": "12",
            "width": "10",
            "height": "4",
            "distance_unit": "in",
            "weight": "2",
            "mass_unit": "lb"
        }],
        "async": False
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if "rates" in data and len(data["rates"]) > 0:
            rate_id = data["rates"][0]["object_id"]
            txn_url = "https://api.goshippo.com/transactions/"
            txn_payload = {"rate": rate_id, "async": False}
            txn_response = requests.post(txn_url, json=txn_payload, headers=headers)
            txn_data = txn_response.json()
            if txn_data.get("status") == "SUCCESS":
                return True, txn_data.get("label_url")
            else:
                return False, f"Shippo Transaction Error: {txn_data}"
        else:
            return False, f"Shippo Rates Error: Could not generate rates for addresses provided. Verify Zip Codes. {data}"
    except Exception as e:
        return False, f"Shippo Exception: {e}"

# ==========================================
# 🛑 LOGIN / SIGN UP WALL
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>⭐ Thrift Star</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Sign in to start swapping.</h4>", unsafe_allow_html=True)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Login")
            email_login = st.text_input("Email", key="login_email")
            password_login = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": password_login})
                    st.session_state.user = res.user
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    
                    new_device_id = str(uuid.uuid4())
                    st.query_params["device"] = new_device_id
                    save_session(new_device_id, res.session.access_token, res.session.refresh_token)
                    
                    st.rerun()
                except Exception as e:
                    st.error("Login Failed: Please check your credentials.")
    with col2:
        with st.container(border=True):
            st.subheader("Create Account")
            username_signup = st.text_input("Desired Username")
            email_signup = st.text_input("Email", key="signup_email")
            password_signup = st.text_input("Password", type="password", key="signup_password")
            if st.button("Sign Up"):
                if username_signup and email_signup and password_signup:
                    try:
                        res = supabase.auth.sign_up({"email": email_signup, "password": password_signup})
                        new_user = res.user
                        if new_user and res.session:
                            st.session_state.user = new_user
                            st.session_state.access_token = res.session.access_token
                            st.session_state.refresh_token = res.session.refresh_token
                            
                            new_device_id = str(uuid.uuid4())
                            st.query_params["device"] = new_device_id
                            save_session(new_device_id, res.session.access_token, res.session.refresh_token)
                            
                            supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
                            supabase.table("users").insert({
                                "id": new_user.id,
                                "username": username_signup,
                                "email": email_signup
                            }).execute()
                            st.success("Account created! You are now logged in.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Sign Up Failed: {e}")
                else:
                    st.error("Please fill out all fields.")
    st.stop()

# ==========================================
# ✅ MAIN THRIFT STAR APP (LOGGED IN)
# ==========================================
ME_ID = st.session_state.user.id
me_data = get_user_by_id(ME_ID)
ME_NAME = me_data["username"] if me_data else "User"

def get_my_items():
    return supabase.table("items").select("*").eq("owner_id", ME_ID).order("id").execute().data

def get_feed_items():
    return supabase.table("items").select("*, users!inner(username)").neq("owner_id", ME_ID).eq('status', 'Available').execute().data

def get_item_by_id(item_id):
    res = supabase.table("items").select("*").eq("id", item_id).execute()
    return res.data[0] if res.data else None

def get_cart_items():
    res = supabase.table("cart_items").select("*, items!inner(*, users!inner(username))").eq("user_id", ME_ID).execute()
    return res.data

st.title("⭐ Thrift Star")
st.markdown("*The premier marketplace for thrifters to buy, sell, and **SWAP**.*")
st.divider()

menu = ["Home Feed", "Shopping Cart", "Negotiations & Offers", "My Closet", "Purchases & Sales", "Profile & Settings"]
choice = st.sidebar.radio("Navigation", menu)
st.sidebar.divider()
st.sidebar.markdown(f"**🟢 Online as:** `{ME_NAME}`")
st.sidebar.button("Log Out", on_click=logout)

# ----------------------------
# DYNAMIC ROUTING COMPONENTS
# ----------------------------

def render_isolated_item_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(view_item=None))
    colA, colB = st.columns([1, 1])
    with colA:
        if item.get('photos') and len(item['photos']) > 0:
            st.image(item['photos'][0], use_container_width=True)
        else:
            st.image("https://placehold.co/600x600/333/FFF?text=No+Image", use_container_width=True)
    with colB:
        st.subheader(f"{item['brand']} {item['listing_title']}")
        seller = get_user_by_id(item['owner_id'])
        st.markdown(f"**Seller:** {seller['username']}")
        st.markdown(f"**Size:** {item['size']} | **Condition:** {item['condition']}")
        st.markdown(f"**Price:** ${item['price']}")
        st.write("**Description:**")
        st.write(item['description'])
        st.write(f"**Tags:** {', '.join(item.get('listing_tags') or [])}")
        
        st.divider()
        if item['owner_id'] != ME_ID and item['status'] == 'Available':
            act_cols = st.columns(2)
            with act_cols[0]:
                if st.button("🛒 Add to Cart", key=f"isocart_{item['id']}"):
                    try:
                        supabase.table("cart_items").insert({"user_id": ME_ID, "item_id": item['id']}).execute()
                        st.success("Added to Cart!")
                    except:
                        st.error("Already in cart.")
            with act_cols[1]:
                if st.button("⚡ Buy Now", key=f"isobuy_{item['id']}"):
                    st.session_state.checkout_item = item
                    st.session_state.view_item = None
                    st.rerun()
            
            with st.expander("🤝 Propose a Swap"):
                my_items = get_my_items()
                if not my_items:
                    st.warning("You don't have any items in your closet to swap!")
                else:
                    item_options = {i["listing_title"]: i for i in my_items}
                    offer_item_name = st.selectbox("Select from your closet:", list(item_options.keys()), key=f"isoselect_{item['id']}")
                    cash_boot = st.number_input("Add cash to your offer ($)?", min_value=0, value=0, step=10, key=f"isocash_{item['id']}")
                    if st.button("Send Swap Offer", key=f"isobtn_{item['id']}"):
                        offered_item = item_options[offer_item_name]
                        new_proposal = {
                            "original_proposer_id": ME_ID,
                            "original_receiver_id": item["owner_id"],
                            "item_wanted_id": item["id"],
                            "item_offered_id": offered_item["id"],
                            "cash_added": cash_boot,
                            "status": "Action Required",
                            "action_with_id": item["owner_id"]
                        }
                        supabase.table("swap_proposals").insert(new_proposal).execute()
                        st.success("Swap proposal sent!")
            with st.expander("💵 Make a Cash Offer"):
                offer_amt = st.number_input("Your Offer Amount ($)", min_value=1, value=int(item['price']), key=f"isocashoff_{item['id']}")
                if st.button("Send Offer", key=f"isosend_offer_{item['id']}"):
                    new_offer = {
                        "original_proposer_id": ME_ID,
                        "original_receiver_id": item["owner_id"],
                        "item_wanted_id": item["id"],
                        "item_offered_id": None,
                        "cash_added": offer_amt,
                        "status": "Action Required",
                        "action_with_id": item["owner_id"]
                    }
                    supabase.table("swap_proposals").insert(new_offer).execute()
                    st.success("Cash offer sent!")

def render_checkout_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(checkout_item=None))
    st.subheader("Secure Checkout Tracker")
    col1, col2 = st.columns(2)
    with col1:
        st.image(item['photos'][0] if item.get('photos') else "https://placehold.co/400", width=250)
        st.markdown(f"**{item['brand']} {item['listing_title']}**")
        seller = get_user_by_id(item['owner_id'])
        st.caption(f"Seller: {seller['username']}")
        if seller and seller.get('paypal_email'):
            st.success(f"✅ Seller has a linked PayPal Account. Funds will be routed seamlessly.")
        else:
            st.warning("⚠️ Seller has not linked a PayPal account. Escrow hold applied.")
    with col2:
        with st.container(border=True):
            subtotal = float(item['price'])
            app_fee = round(subtotal * 0.10, 2)
            total = subtotal + app_fee
            st.markdown("### Order Summary")
            st.markdown(f"Subtotal: **${subtotal:.2f}**")
            st.markdown(f"ThriftStar Fee (10%): **${app_fee:.2f}**")
            st.divider()
            st.markdown(f"## Total: ${total:.2f}")
            payment_method = st.radio("Select Method", ["PayPal", "Credit Card / Debit Card"])
            if st.button("Complete Purchase", type="primary"):
                addr = me_data.get('address')
                if not addr or not addr.get("street1"):
                    st.error("Please insert your Address in Profile & Settings before checking out so we can track shipping!")
                else:
                    with st.spinner(f"Processing ${total:.2f} via {payment_method}..."):
                        success, message_or_id = process_sandbox_payment(total)
                        if success:
                            supabase.table("orders").insert({
                                "buyer_id": ME_ID,
                                "seller_id": item["owner_id"],
                                "item_id": item["id"],
                                "amount": total,
                                "braintree_txn_id": message_or_id
                            }).execute()
                            supabase.table("items").update({"status": "Sold"}).eq("id", item["id"]).execute()
                            st.session_state.checkout_item = None
                            st.success("Purchase Successful! Track your label in 'Purchases & Sales'.")
                            st.rerun()
                        else:
                            st.error(f"Payment Failed: {message_or_id}")

# ----------------------------
# PAGE ROUTING
# ----------------------------

if st.session_state.view_item is not None:
    render_isolated_item_page(st.session_state.view_item)
    st.stop()
    
if st.session_state.checkout_item is not None:
    render_checkout_page(st.session_state.checkout_item)
    st.stop()


if choice == "Home Feed":
    st.subheader("Discover Items")
    feed = get_feed_items()
    if not feed:
        st.info("No available items in the feed right now.")
    else:
        cols = st.columns(3)
        for index, item in enumerate(feed):
            with cols[index % 3]:
                with st.container(border=True):
                    image_url = item['photos'][0] if item.get('photos') and len(item['photos']) > 0 else "https://placehold.co/400x400/333/FFF?text=No+Image"
                    st.image(image_url, use_container_width=True)
                    st.markdown(f"### {item['brand']}")
                    st.markdown(f"**{item['listing_title']}**")
                    st.markdown(f"**${item['price']}**")
                    if st.button("🔍 View Details", key=f"view_{item['id']}"):
                        st.session_state.view_item = item
                        st.rerun()

elif choice == "Shopping Cart":
    st.subheader("Your Shopping Cart")
    cart_items = get_cart_items()
    if not cart_items:
        st.info("Your cart is empty.")
    else:
        subtotal_price = 0
        for c in cart_items:
            item = c['items']
            subtotal_price += item['price']
            with st.container(border=True):
                colA, colB, colC = st.columns([1, 4, 1])
                with colA:
                    st.image(item['photos'][0] if item.get('photos') else "https://placehold.co/400", use_container_width=True)
                with colB:
                    st.markdown(f"**{item['brand']} {item['listing_title']}**")
                    st.markdown(f"### ${item['price']}")
                with colC:
                    if st.button("❌ Remove", key=f"rm_cart_{c['id']}"):
                        supabase.table("cart_items").delete().eq("id", c['id']).execute()
                        st.rerun()
        st.divider()
        app_fee = round(subtotal_price * 0.10, 2)
        total_price = subtotal_price + app_fee
        st.markdown(f"**Subtotal:** ${subtotal_price:.2f}")
        st.markdown(f"**ThriftStar Fee (10%):** ${app_fee:.2f}")
        st.markdown(f"## Total: ${total_price:.2f}")
        st.radio("Payment Method", ["PayPal Dashboard", "Credit Card"])
        if st.button("💳 Confirm Checkout & Pay", type="primary"):
            addr = me_data.get('address')
            if not addr or not addr.get("street1"):
                st.error("Please add a Shipping Address in Profile & Settings before checking out.")
            else:
                with st.spinner("Authorizing..."):
                    success, txn = process_sandbox_payment(total_price)
                    if success:
                        for c in cart_items:
                            item = c['items']
                            supabase.table("orders").insert({
                                "buyer_id": ME_ID,
                                "seller_id": item["owner_id"],
                                "item_id": item["id"],
                                "amount": item["price"] * 1.10,
                                "braintree_txn_id": txn
                            }).execute()
                            supabase.table("items").update({"status": "Sold"}).eq("id", item["id"]).execute()
                            supabase.table("cart_items").delete().eq("id", c['id']).execute()
                        st.success("Checkout Successful!")
                        st.rerun()
                    else:
                        st.error(f"Checkout Failed: {txn}")

elif choice == "Purchases & Sales":
    st.subheader("Order History & Shipping Logistics")
    orders_res = supabase.table("orders").select("*, items!inner(*), buyer:users!orders_buyer_id_fkey(*), seller:users!orders_seller_id_fkey(*)").or_(f"buyer_id.eq.{ME_ID},seller_id.eq.{ME_ID}").order("created_at", desc=True).execute()
    orders = orders_res.data
    if not orders:
        st.info("No orders found.")
    else:
        for o in orders:
            item = o['items']
            im_buyer = o['buyer_id'] == ME_ID
            role = "BUYER" if im_buyer else "SELLER"
            other_name = o['seller']['username'] if im_buyer else o['buyer']['username']
            with st.container(border=True):
                st.markdown(f"**[{role}]** {item['brand']} {item['listing_title']} - **${o['amount']}**")
                st.caption(f"Order ID: {o['id']} | Txn: {o['braintree_txn_id']}")
                if st.button(f"📦 Generate Auto-Routing Label", key=f"label_{o['id']}"):
                    with st.spinner("Generating Live USPS Label from Profiles..."):
                        if im_buyer:
                            # If buyer, label goes from Seller to Buyer
                            success, label_or_err = create_shipping_label(o['seller']['id'], o['buyer']['id'])
                        else:
                            success, label_or_err = create_shipping_label(o['seller']['id'], o['buyer']['id'])
                            
                        if success:
                            st.markdown(f"📥 **[Download USPS Shipping Label PDF]({label_or_err})**")
                        else:
                            st.error(f"Shippo Generation Failed: {label_or_err}")

elif choice == "Negotiations & Offers":
    st.subheader("Active Proposals")
    prop_res = supabase.table("swap_proposals").select("*").or_(f"original_proposer_id.eq.{ME_ID},original_receiver_id.eq.{ME_ID}").order("updated_at", desc=True).execute()
    if not prop_res.data:
        st.info("No active proposals right now.")
    else:
        for p in prop_res.data:
            with st.container(border=True):
                am_i_proposer = p["original_proposer_id"] == ME_ID
                other_user_id = p["original_receiver_id"] if am_i_proposer else p["original_proposer_id"]
                is_cash_offer = p["item_offered_id"] is None
                their_item_id = p["item_wanted_id"] if am_i_proposer else p["item_offered_id"]
                their_item = get_item_by_id(their_item_id) if their_item_id else None
                other_username = get_user_by_id(other_user_id)["username"]
                
                st.markdown(f"### {'💵 Cash Offer' if is_cash_offer else '🔄 Item Swap'} with {other_username}")
                if is_cash_offer:
                    verb = "You offered" if am_i_proposer else "They offered"
                    st.markdown(f"**{verb} ${p['cash_added']}** for **{their_item['brand']} {their_item['listing_title']}**")
                
                if p["status"] == "Accepted":
                    if p.get("braintree_txn_id"): st.success("Deal Finalized!")
                    else: st.success("Accepted! Proceeding to Shipping.")
                        
                    if st.button("Generate Swap Label", key=f"sship_{p['id']}"):
                        s1, err = create_shipping_label(ME_ID, other_user_id)
                        if s1: st.markdown(f"📥 **[Download Label to Send to {other_username}]({err})**")
                        else: st.error(err)
                elif p["status"] == "Declined":
                    st.error("Declined.")
                else:
                    if p["action_with_id"] != ME_ID:
                        st.warning("Waiting for response...")
                    else:
                        st.success("Your turn to respond!")
                        if st.button("✅ Accept", key=f"acc_{p['id']}", type="primary"):
                            addr = me_data.get('address')
                            if not addr or not addr.get('street1'):
                                st.error("Please add a Shipping Address in Profile & Settings before accepting!")
                            else:
                                update_payload = {"status": "Accepted", "action_with_id": None}
                                if p['cash_added'] > 0 and (am_i_proposer if is_cash_offer else am_i_proposer):
                                    success, message_or_id = process_sandbox_payment(p['cash_added'])
                                    if success: update_payload["braintree_txn_id"] = message_or_id
                                supabase.table("swap_proposals").update(update_payload).eq("id", p["id"]).execute()
                                st.rerun()

elif choice == "Profile & Settings":
    st.subheader("User Profile & Location Configuration")
    st.info("The addresses saved here are securely pipelined directly to the Shippo Logistics API for all live transactions.")
    with st.form("profile_form"):
        st.write("### Public Profile")
        new_name = st.text_input("Full Name", value=me_data.get('full_name', ''))
        new_bio = st.text_area("Bio", value=me_data.get('bio', ''))
        
        st.write("### Private Shipping & Contact Details")
        addr = me_data.get('address') or {}
        col1, col2 = st.columns(2)
        with col1:
            street = st.text_input("Street Address", value=addr.get('street1', ''))
            city = st.text_input("City", value=addr.get('city', ''))
        with col2:
            state = st.text_input("State", value=addr.get('state', ''))
            zip_code = st.text_input("ZIP Code", value=addr.get('zip', ''))
        
        new_phone = st.text_input("Phone Number", value=me_data.get('phone_number', ''))
        
        st.write("### Seller Payouts")
        new_paypal = st.text_input("PayPal Email Address", value=me_data.get('paypal_email', ''))
        
        if st.form_submit_button("Save Profile Defaults"):
            address_json = {
                "name": new_name or ME_NAME,
                "street1": street,
                "city": city,
                "state": state,
                "zip": zip_code,
                "country": "US",
                "phone": new_phone
            }
            res = supabase.table("users").update({
                "full_name": new_name,
                "bio": new_bio,
                "phone_number": new_phone,
                "paypal_email": new_paypal,
                "address": address_json
            }).eq("id", ME_ID).execute()
            st.success("Global Profile routing parameters updated successfully!")

elif choice == "My Closet":
    st.subheader("My Inventory")
    my_items = get_my_items()
    if not my_items:
        st.info("Your closet is empty. Add some items!")
    else:
        closet_cols = st.columns(4)
        for index, item in enumerate(my_items):
            with closet_cols[index % 4]:
                with st.container(border=True):
                    st.image(item['photos'][0] if item.get('photos') else "https://placehold.co/400", use_container_width=True)
                    st.markdown(f"**{item['brand']}**")
                    st.markdown(f"{item['listing_title']}")
                    if st.button("🔍 View", key=f"cview_{item['id']}"):
                        st.session_state.view_item = item
                        st.rerun()

    st.divider()
    st.subheader("Add New Item")
    with st.form("add_item"):
        col1, col2 = st.columns(2)
        with col1:
            brand = st.text_input("Brand")
            name = st.text_input("Item Name (Listing Title)")
            category = st.selectbox("Category", ["Tops", "Bottoms", "Outerwear", "Sneakers", "Accessories", "Other"])
            size = st.text_input("Size")
            price = st.number_input("Estimated Value / Buy Now Price ($)", min_value=1.0)
            condition = st.selectbox("Condition", ['New', 'Gently Used', 'Used', 'Very Worn'])
        with col2:
            st.write("Upload Photo")
            uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])
            desc = st.text_area("Description")
            
        if st.form_submit_button("List Item"):
            if brand and name:
                image_urls = []
                if uploaded_file is not None:
                    ext = uploaded_file.name.split(".")[-1]
                    fname = f"{uuid.uuid4()}.{ext}"
                    try:
                        s3_client.put_object(Bucket=S3_BUCKET, Key=fname, Body=uploaded_file.getvalue(), ContentType=uploaded_file.type)
                        image_urls.append(f"{url}/storage/v1/object/public/{S3_BUCKET}/{fname}")
                    except Exception as e:
                        st.error(f"S3 Error: {e}")
                        st.stop()
                
                try:
                    res = supabase.table("items").insert({
                        "owner_id": ME_ID, "brand": brand, "listing_title": name,
                        "category": category, "size": size, "price": price,
                        "condition": condition, "description": desc, "photos": image_urls 
                    }).execute()
                    if res.data:
                        st.success("Item saved!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")
