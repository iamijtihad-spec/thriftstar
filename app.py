import streamlit as st
import pandas as pd
import braintree
import boto3
import os
import uuid
import requests
import json
import base64
from streamlit_cookies_controller import CookieController
from PIL import Image
import io
from dotenv import load_dotenv
import streamlit.components.v1 as components
from supabase import create_client, Client

# --- DUAL-MODE SECRET LOADER ---
load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

# Set page config FIRST
st.set_page_config(
    page_title="Thrift Star",
    layout="wide",
    page_icon="⭐",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALIZATION ---
for key, val in {
    "user": None, "access_token": None, "refresh_token": None,
    "view_item": None, "checkout_item": None,
    "active_checkout_type": None, "active_checkout_id": None, "active_checkout_amount": 0,
    "pending_accept_id": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
    endpoint_url=f"{url}/storage/v1/s3",
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
except Exception:
    braintree_configured = False

# Initialize Shippo
SHIPPO_API_KEY = get_secret("SHIPPO_API_KEY")
shippo_configured = bool(SHIPPO_API_KEY)

# --- IMAGE LOADER HELPER ---
def get_data_uri(path):
    """Safely loads JPG/PNG and returns an HTML-ready data URI."""
    try:
        ext = path.split('.')[-1].lower()
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

# Load all custom sketches
URI_VEND   = get_data_uri("sketch_blunt_vending_machine_2.png")
URI_BURGER = get_data_uri("sketch_fire_2.png")   # lighter/fire used as burger-divider art
URI_WOOF   = get_data_uri("sketch_woof_2.png")
URI_SHOE   = get_data_uri("sketch_shoe_2.png")
URI_BG     = get_data_uri("icon.png")            # app icon for sidebar logo


# --- REUSABLE UI COMPONENTS ---
def burger_divider():
    if URI_BURGER:
        st.markdown(
            f'<div class="burger-divider"><hr><img src="{URI_BURGER}" alt="divider"><hr></div>',
            unsafe_allow_html=True
        )
    else:
        st.divider()

def empty_state(img_uri, title, subtitle):
    img_html = f'<img src="{img_uri}">' if img_uri else ''
    st.markdown(f"""
    <div class="empty-state">
        {img_html}
        <h3>{title}</h3>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# --- PREMIUM UI DESIGN SYSTEM ---
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
/* Base White Theme */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #FFFFFF !important;
    color: #1A1A1C !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stMain"] { background-color: #FFFFFF !important; }
[data-testid="block-container"] { padding-top: 1.5rem !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], header[data-testid="stHeader"] {
    visibility: hidden !important;
    height: 0 !important;
}

/* Sidebar (Clean White/Gray) */
[data-testid="stSidebar"] {
    background: #F7F7F7 !important;
    border-right: 1px solid #EAEAEA !important;
}
[data-testid="stSidebarNav"] { padding-top: 1rem !important; }

/* Metric & Headings */
h1 { font-family: 'Bebas Neue', sans-serif !important; color: #F5A623 !important; letter-spacing: 2px !important; }
h2 { font-family: 'Bebas Neue', sans-serif !important; color: #1A1A1C !important; letter-spacing: 1px !important; }
p, li, label, span { color: #555 !important; }

/* Buttons & Inputs */
.stButton > button {
    border-radius: 20px !important;
    font-weight: 600 !important;
    border: 1px solid #EAEAEA !important;
    background: white !important;
    color: #1A1A1C !important;
}
.stButton > button:hover {
    background: #F5A623 !important;
    border-color: #F5A623 !important;
}
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #F9F9F9 !important;
    border: 1px solid #EAEAEA !important;
    color: #1A1A1C !important;
}

/* Grailed Card Style */
.grailed-card {
    background: white;
    border: 1px solid #EAEAEA;
    border-radius: 8px;
    padding: 0;
    overflow: hidden;
    margin-bottom: 1.5rem;
    transition: all 0.2s ease;
}
.grailed-card:hover { border-color: #F5A623; transform: translateY(-3px); }
.grailed-card .card-info { padding: 8px 12px 12px; }
.grailed-card .card-brand { font-family: 'Bebas Neue'; font-size: 1.1rem; color: #1A1A1C; }
.grailed-card .card-title { font-size: 0.75rem; color: #888; margin-top: 2px; }
.grailed-card .card-price { font-family: 'Bebas Neue'; color: #F5A623; font-size: 1.4rem; }

/* DM Bubbles */
.dm-bubble { border-radius: 18px; padding: 10px 15px; font-size: 0.9rem; }
.dm-bubble.sent { background: #F5A623; color: black !important; margin-left: auto; }
.dm-bubble.received { background: #F0F0F0; color: black !important; margin-right: auto; }

/* DM Header */
.dm-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; padding: 10px; background: #fafafa; border-radius: 8px; border: 1px solid #eee; }
.dm-avatar { width: 40px; height: 40px; border-radius: 50%; background: #F5A623; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.dm-status-pill { padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.dm-status-pill.pending { background: #EAEAEA; color: #666; }
.dm-status-pill.accepted { background: #00C864; color: white; }
.dm-status-pill.declined { background: #FF3C3C; color: white; }
</style>
""") # Fixed: removed unsafe_allow_html=True


# ==========================================
# SESSION MANAGEMENT & PERSISTENCE
# ==========================================
cookie_manager = CookieController()

# Attempt to restore session from Browser Cookies on page load
saved_access = cookie_manager.get("ts_access_token")
saved_refresh = cookie_manager.get("ts_refresh_token")

if saved_access and saved_refresh and st.session_state.user is None:
    try:
        res = supabase.auth.set_session(saved_access, saved_refresh)
        if res.user:
            st.session_state.user = res.user
            st.session_state.access_token = saved_access
            st.session_state.refresh_token = saved_refresh
    except Exception:
        cookie_manager.remove("ts_access_token")
        cookie_manager.remove("ts_refresh_token")

# Re-apply session state to the Supabase client to ensure thread safety
if st.session_state.user and st.session_state.access_token:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except Exception:
        pass

def login_user(access_token, refresh_token, user):
    """Helper to set state and cookies upon successful login/signup"""
    st.session_state.user = user
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    cookie_manager.set("ts_access_token", access_token, max_age=604800) # 7 days
    cookie_manager.set("ts_refresh_token", refresh_token, max_age=604800)

def logout():
    try: 
        supabase.auth.sign_out()
    except Exception: 
        pass
    cookie_manager.remove("ts_access_token")
    cookie_manager.remove("ts_refresh_token")
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.checkout_item = None
    st.session_state.view_item = None
    st.rerun()

def get_user_by_id(user_id):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def get_braintree_client_token():
    if not braintree_configured: return None
    try: return gateway.client_token.generate()
    except Exception: return None

def process_braintree_transaction(amount, nonce):
    if not braintree_configured: return False, "Braintree gateway not configured."
    result = gateway.transaction.sale({
        "amount": f"{amount:.2f}",
        "payment_method_nonce": nonce,
        "options": {"submit_for_settlement": True}
    })
    if result.is_success: return True, result.transaction.id
    return False, result.message

def render_braintree_dropin(amount, label="VERIFY PAYMENT", target_id="checkout"):
    token = get_braintree_client_token()
    if not token:
        st.error("Payment Gateway unreachable.")
        return
    dropin_html = f"""
    <script src="https://js.braintreegateway.com/web/dropin/1.42.0/js/dropin.min.js"></script>
    <div id="dropin-container"></div>
    <button id="submit-button" style="background:#000; color:white; border:none; padding:12px 24px; border-radius:4px; font-family:sans-serif; cursor:pointer; width:100%; font-weight:700; margin-top:10px;">{label}</button>
    <script>
        const button = document.querySelector('#submit-button');
        braintree.dropin.create({{
            authorization: '{token}',
            container: '#dropin-container',
            paypal: {{ flow: 'vault' }}
        }}, (error, instance) => {{
            if (error) console.error(error);
            button.addEventListener('click', () => {{
                instance.requestPaymentMethod((error, payload) => {{
                    if (error) console.error(error);
                    const url = new URL(window.top.location.href);
                    url.searchParams.set('payment_nonce', payload.nonce);
                    url.searchParams.set('payment_target', '{target_id}');
                    window.top.location.href = url.href;
                }});
            }});
        }});
    </script>
    """
    components.html(dropin_html, height=550)
    if st.button("Reset Payment State", key=f"reset_{target_id}"):
        st.query_params.clear()
        st.rerun()


# ==========================================
# 📦 LOGISTICS & SHIPPO FLOW
# ==========================================
def get_live_shipping_rate(sender_id, receiver_id):
    """Fetches the lowest available shipping rate before checkout."""
    if not shippo_configured: return False, 0.0, "Shippo not configured.", None
    sender = get_user_by_id(sender_id)
    receiver = get_user_by_id(receiver_id)
    if not sender or not receiver: return False, 0.0, "Users not found.", None
    
    addr_from = sender.get('address', {}).copy()
    addr_to = receiver.get('address', {}).copy()
    if not addr_from.get('street1') or not addr_to.get('street1'):
        return False, 0.0, "Missing shipping addresses in Profile.", None

    # Standardize for Shippo
    addr_from.update({"country": "US", "name": sender.get("username", "Seller")})
    addr_to.update({"country": "US", "name": receiver.get("username", "Buyer")})

    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "address_from": addr_from, "address_to": addr_to,
        "parcels": [{"length":"12","width":"10","height":"4","distance_unit":"in","weight":"2","mass_unit":"lb"}],
        "async": False
    }
    try:
        response = requests.post("https://api.goshippo.com/shipments/", json=payload, headers=headers).json()
        if "rates" in response and len(response["rates"]) > 0:
            rates = sorted(response["rates"], key=lambda x: float(x['amount']))
            lowest_rate = rates[0]
            return True, float(lowest_rate['amount']), "Success", lowest_rate['object_id']
        return False, 0.0, "No rates found for this route.", None
    except Exception as e:
        return False, 0.0, f"Shippo API Error: {e}", None

def purchase_shipping_label(rate_id):
    """Actually buys the label using the rate ID locked in at checkout."""
    if not rate_id: return False, "No valid rate ID provided."
    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}", "Content-Type": "application/json"}
    try:
        txn = requests.post("https://api.goshippo.com/transactions/", json={"rate": rate_id, "async": False}, headers=headers).json()
        if txn.get("status") == "SUCCESS":
            return True, txn.get("label_url")
        return False, str(txn.get("messages", "Failed to purchase label."))
    except Exception as e:
        return False, str(e)


# ==========================================
# 🛑 AUTHENTICATION WALL
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align:center;'>⭐ THRIFT STAR</h1>", unsafe_allow_html=True)
    if URI_VEND:
        st.markdown(f'<div style="text-align:center;"><img src="{URI_VEND}" style="width:200px;"/></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Login")
            e_login = st.text_input("Email", key="l_e")
            p_login = st.text_input("Password", type="password", key="l_p")
            if st.button("Sign In", type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e_login, "password": p_login})
                    login_user(res.session.access_token, res.session.refresh_token, res.user)
                    st.rerun()
                except Exception: st.error("Login Failed.")
    with col2:
        with st.container(border=True):
            st.subheader("Sign Up")
            u_signup = st.text_input("Username")
            e_signup = st.text_input("Email", key="s_e")
            p_signup = st.text_input("Password", type="password", key="s_p")
            if st.button("Create Account"):
                try:
                    res = supabase.auth.sign_up({"email": e_signup, "password": p_signup})
                    if res.user and res.session:
                        login_user(res.session.access_token, res.session.refresh_token, res.user)
                        supabase.table("users").insert({"id": res.user.id, "username": u_signup, "email": e_signup}).execute()
                        st.rerun()
                except Exception as e: st.error(f"Sign Up Failed: {e}")
    st.stop()


# ==========================================
# ✅ MAIN APPLICATION
# ==========================================
ME_ID   = st.session_state.user.id
me_data = get_user_by_id(ME_ID)
ME_NAME = me_data["username"] if me_data else "User"

def get_my_items(): return supabase.table("items").select("*").eq("owner_id", ME_ID).order("id").execute().data
def get_feed_items(): return supabase.table("items").select("*, users!inner(username)").neq("owner_id", ME_ID).eq('status', 'Available').execute().data
def get_item_by_id(item_id):
    res = supabase.table("items").select("*").eq("id", item_id).execute()
    return res.data[0] if res.data else None
def get_cart_items(): return supabase.table("cart_items").select("*, items!inner(*, users!inner(username))").eq("user_id", ME_ID).execute().data

# UI Page Layout
with st.sidebar:
    if URI_VEND: st.markdown(f'<div style="text-align:center;"><img src="{URI_VEND}" style="width:100px; opacity:0.8;"/></div>', unsafe_allow_html=True)
    st.divider()
    menu = ["Home Feed", "Shopping Cart", "Negotiations & Offers", "My Closet", "Purchases & Sales", "Profile & Settings"]
    choice = st.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.markdown(f"**🟢 Online as:** `{ME_NAME}`")
    st.sidebar.button("Log Out", on_click=logout)

st.title("⭐ Thrift Star")
st.markdown("*Buy · Sell · Swap Streetwear*")


# --- ISOLATED ITEM PAGE ---
def render_isolated_item_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(view_item=None))
    burger_divider()
    colA, colB = st.columns([1, 1])
    with colA:
        if item.get('photos'): st.image(item['photos'][0], use_container_width=True)
        else: st.image("https://placehold.co/600x600?text=No+Image", use_container_width=True)
    with colB:
        st.subheader(f"{item['brand']} {item['listing_title']}")
        st.markdown(f"**Price:** ${item['price']} | **Size:** {item.get('size','OS')}")
        st.write(item.get('description', ''))
        st.divider()
        if item['owner_id'] != ME_ID and item['status'] == 'Available':
            c1, c2 = st.columns(2)
            if c1.button("Add to Cart"):
                supabase.table("cart_items").insert({"user_id": ME_ID, "item_id": item['id']}).execute()
                st.toast("Added to Cart!")
            if c2.button("Buy Now", type="primary"):
                st.session_state.checkout_item = item
                st.session_state.view_item = None
                st.rerun()

# --- CHECKOUT PAGE (BUY NOW) ---
def render_checkout_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(checkout_item=None))
    burger_divider()
    st.subheader("Secure Checkout")
    
    # 1. Fetch Shipping Rate (Locked)
    if "c_rate" not in st.session_state or st.session_state.get("c_id") != item['id']:
        with st.spinner("Fetching Live USPS Rate..."):
            ok, cost, msg, rid = get_live_shipping_rate(item['owner_id'], ME_ID)
            if ok:
                st.session_state.c_rate = cost
                st.session_state.c_rid = rid
                st.session_state.c_id = item['id']
            else:
                st.error(msg); st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.image(item['photos'][0] if item.get('photos') else "https://placehold.co/400", width=250)
        st.markdown(f"**{item['brand']} {item['listing_title']}**")
    with col2:
        with st.container(border=True):
            sub = float(item['price'])
            fee = round(sub * 0.10, 2)
            shp = st.session_state.c_rate
            tot = sub + fee + shp
            st.markdown(f"**Subtotal:** ${sub:.2f}\n\n**App Fee:** ${fee:.2f}\n\n**Shipping:** ${shp:.2f}")
            st.markdown(f"## Total: ${tot:.2f}")
            
            nonce = st.query_params.get("payment_nonce")
            if nonce and st.query_params.get("payment_target") == f"item_{item['id']}":
                st.success("Payment Verified.")
                if st.button("Complete Purchase", type="primary"):
                    with st.spinner("Processing..."):
                        p_ok, p_txn = process_braintree_transaction(tot, nonce)
                        if p_ok:
                            l_ok, l_url = purchase_shipping_label(st.session_state.c_rid)
                            supabase.table("orders").insert({
                                "buyer_id": ME_ID, "seller_id": item["owner_id"],
                                "item_id": item["id"], "amount": tot,
                                "braintree_txn_id": p_txn, "shipping_label_url": l_url if l_ok else None
                            }).execute()
                            supabase.table("items").update({"status": "Sold"}).eq("id", item["id"]).execute()
                            supabase.table("cart_items").delete().eq("item_id", item["id"]).execute()
                            st.query_params.clear()
                            st.success("Success! 🛍️")
                            st.session_state.checkout_item = None
                            st.rerun()
                        else: st.error(p_txn)
            else:
                render_braintree_dropin(tot, f"PAY ${tot:.2f}", target_id=f"item_{item['id']}")

# Global Redirects
if st.session_state.view_item: render_isolated_item_page(st.session_state.view_item); st.stop()
if st.session_state.checkout_item: render_checkout_page(st.session_state.checkout_item); st.stop()


# ==========================================
# PAGE CONTENT ROUTING
# ==========================================
if choice == "Home Feed":
    st.markdown("<h2>DISCOVER HEAT</h2>", unsafe_allow_html=True)
    feed = get_feed_items()
    if not feed: empty_state(URI_SHOE, "No heat found.", "List something first.")
    else:
        cols = st.columns(4)
        for idx, itm in enumerate(feed):
            with cols[idx % 4]:
                st.markdown(f"""<div class="grailed-card"><img src="{itm['photos'][0]}"><div class="card-info"><div class="card-brand">{itm['brand']}</div><div class="card-price">${itm['price']}</div></div></div>""", unsafe_allow_html=True)
                if st.button("View Details", key=f"f_v_{itm['id']}"):
                    st.session_state.view_item = itm; st.rerun()

elif choice == "Shopping Cart":
    st.markdown("<h2>YOUR WISHLIST</h2>", unsafe_allow_html=True)
    st.info("Direct multi-item checkout is coming soon. For now, please use the 'Buy Now' button on individual items to ensure accurate shipping and secure payments.")
    items = get_cart_items()
    if not items:
        empty_state(URI_WOOF, "Your wishlist is empty.", "Go back to the feed to find some steals.")
    else:
        for c in items:
            itm = c['items']
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 4, 1.5])
                with col1:
                    st.image(itm['photos'][0] if itm.get('photos') else "https://placehold.co/400", use_container_width=True)
                with col2:
                    st.markdown(f"**{itm['brand']}** - {itm['listing_title']}")
                    st.markdown(f"### ${itm['price']}")
                with col3:
                    if st.button("Buy Now", key=f"cart_buy_{itm['id']}", type="primary"):
                        st.session_state.checkout_item = itm
                        st.rerun()
                    if st.button("Remove", key=f"cart_rm_{c['id']}"):
                        supabase.table("cart_items").delete().eq("id", c['id']).execute()
                        st.rerun()

elif choice == "Negotiations & Offers":
    st.markdown("<h2>NEGOTIATIONS & OFFERS</h2>", unsafe_allow_html=True)
    prop_res = supabase.table("swap_proposals") \
        .select("*") \
        .or_(f"original_proposer_id.eq.{ME_ID},original_receiver_id.eq.{ME_ID}") \
        .order("updated_at", desc=True).execute()
    
    if not prop_res.data:
        empty_state(URI_VEND, "No active proposals.", "Go to the feed and send a swap offer.")
    else:
        for p in prop_res.data:
            am_i_proposer = p["original_proposer_id"] == ME_ID
            other_user_id = p["original_receiver_id"] if am_i_proposer else p["original_proposer_id"]
            is_cash_only  = p["item_offered_id"] is None
            
            item_wanted   = get_item_by_id(p["item_wanted_id"])
            item_offered  = get_item_by_id(p["item_offered_id"]) if p["item_offered_id"] else None
            
            other_user    = get_user_by_id(other_user_id)
            other_name    = other_user["username"] if other_user else "Unknown"
            status        = p["status"]
            status_class  = {"Accepted": "accepted", "Declined": "declined"}.get(status, "pending")
            offer_type    = "💵 Cash Offer" if is_cash_only else "🔄 Item Swap"

            # DM Header
            st.markdown(f"""
            <div class="dm-header">
                <div class="dm-avatar">{other_name[0].upper()}</div>
                <div style="flex:1;">
                    <div style="font-weight:700;font-size:0.95rem;">{other_name}</div>
                    <div style="font-size:0.75rem;color:#666;">{offer_type}</div>
                </div>
                <span class="dm-status-pill {status_class}">{status}</span>
            </div>
            """, unsafe_allow_html=True)

            # Bubble Thread
            side = "sent" if am_i_proposer else "received"
            if is_cash_only and item_wanted:
                text = f"Offered <strong>${p['cash_added']}</strong> for your <strong>{item_wanted['brand']} {item_wanted['listing_title']}</strong>"
            elif item_wanted and item_offered:
                text = f"Offering <strong>{item_offered['brand']}</strong> + ${p['cash_added']} for your <strong>{item_wanted['brand']}</strong>"
            else:
                text = "Offer details unavailable."
                
            st.markdown(f'<div class="dm-thread"><div class="dm-bubble {side}">{text}</div></div>', unsafe_allow_html=True)

            # Action Area
            if status == "Pending":
                if p["action_with_id"] != ME_ID:
                    st.caption("Waiting for their response...")
                else:
                    col_a, col_b, col_c = st.columns([1,1,1])
                    # Counter Offer
                    with col_a:
                        new_cash = st.number_input("Counter ($)", min_value=0, value=int(p['cash_added']), key=f"counter_{p['id']}")
                        if st.button("Send Counter", key=f"btn_c_{p['id']}"):
                            supabase.table("swap_proposals").update({
                                "cash_added": new_cash,
                                "action_with_id": other_user_id,
                                "original_proposer_id": ME_ID, 
                                "original_receiver_id": other_user_id
                            }).eq("id", p["id"]).execute()
                            st.rerun()
                    
                    # Accept Logic (Two-Step Shipping)
                    with col_b:
                        is_accepting = st.session_state.get("pending_accept_id") == p["id"]
                        if not is_accepting:
                            if st.button("Accept Offer", key=f"acc_{p['id']}", type="primary"):
                                st.session_state.pending_accept_id = p["id"]
                                st.rerun()
                        else:
                            st.info("Finalizing Agreement...")
                            # 1. Fetch Shipping Rates for BOTH parties
                            with st.spinner("Locking dual-party logistics..."):
                                # Rate 1: Proposer -> Receiver
                                ok1, cost1, msg1, rid1 = get_live_shipping_rate(p["original_proposer_id"], p["original_receiver_id"])
                                # Rate 2: Receiver -> Proposer (Only if it's a swap)
                                if not is_cash_only:
                                    ok2, cost2, msg2, rid2 = get_live_shipping_rate(p["original_receiver_id"], p["original_proposer_id"])
                                else:
                                    ok2, cost2, rid2 = True, 0.0, None # Cash only, seller doesn't ship back

                            if ok1 and ok2:
                                total_fee = float(p['cash_added']) + 10.0 # Flat TS fee for swaps
                                nonce = st.query_params.get("payment_nonce")
                                if nonce and st.query_params.get("payment_target") == f"offer_{p['id']}":
                                    if st.button("Confirm & Pay", key=f"pay_{p['id']}", type="primary"):
                                        p_ok, p_txn = process_braintree_transaction(total_fee, nonce)
                                        if p_ok:
                                            # Buy labels
                                            l1_ok, l1_url = purchase_shipping_label(rid1)
                                            l2_ok, l2_url = purchase_shipping_label(rid2) if rid2 else (True, None)
                                            
                                            # Finalize Proposal & Orders
                                            supabase.table("swap_proposals").update({"status": "Accepted"}).eq("id", p["id"]).execute()
                                            
                                            # Buy Leg
                                            supabase.table("orders").insert({
                                                "buyer_id": p["original_proposer_id"], "seller_id": p["original_receiver_id"],
                                                "item_id": p["item_wanted_id"], "amount": total_fee,
                                                "braintree_txn_id": p_txn, "shipping_label_url": l1_url
                                            }).execute()
                                            
                                            # Return Leg (if swap)
                                            if not is_cash_only:
                                                supabase.table("orders").insert({
                                                    "buyer_id": p["original_receiver_id"], "seller_id": p["original_proposer_id"],
                                                    "item_id": p["item_offered_id"], "amount": 0.0,
                                                    "braintree_txn_id": "SWAP", "shipping_label_url": l2_url
                                                }).execute()
                                                supabase.table("items").update({"status": "Swapped"}).eq("id", p["item_offered_id"]).execute()

                                            supabase.table("items").update({"status": "Sold" if is_cash_only else "Swapped"}).eq("id", p["item_wanted_id"]).execute()
                                            st.query_params.clear(); st.session_state.pending_accept_id = None; st.rerun()
                                else:
                                    render_braintree_dropin(total_fee, f"PAY ${total_fee:.2f} TO FINALIZE", target_id=f"offer_{p['id']}")
                            else:
                                st.error(f"Logistics Error: {msg1 if not ok1 else msg2}")

                    with col_c:
                        if st.button("Decline", key=f"dec_{p['id']}"):
                            supabase.table("swap_proposals").update({"status": "Declined"}).eq("id", p["id"]).execute()
                            st.rerun()
            elif status == "Accepted":
                st.success("🤝 Deal Finalized. Labels available in Purchases & Sales.")
            st.divider()

elif choice == "My Closet":
    st.markdown("<h2>MY CLOSET</h2>", unsafe_allow_html=True)
    my_items = get_my_items()
    if not my_items:
        empty_state(URI_VEND, "Your closet is bare.", "List some items to start swapping.")
    else:
        closet_cols = st.columns(4)
        for idx, item in enumerate(my_items):
            with closet_cols[idx % 4]:
                st.markdown(f"""<div class="grailed-card"><img src="{item['photos'][0] if item.get('photos') else 'https://placehold.co/400'}"><div class="card-info"><div class="card-brand">{item['brand']}</div><div class="card-price">${item['price']}</div></div></div>""", unsafe_allow_html=True)
                if st.button("View / Edit", key=f"c_v_{item['id']}"):
                    st.session_state.view_item = item; st.rerun()

    burger_divider()
    st.markdown("### Add New Item")
    with st.form("add_item"):
        col1, col2 = st.columns(2)
        with col1:
            brand     = st.text_input("Brand")
            title     = st.text_input("Listing Title")
            category  = st.selectbox("Category", ["Tops", "Bottoms", "Outerwear", "Sneakers", "Accessories", "Other"])
            size      = st.text_input("Size")
            price     = st.number_input("Estimated Value ($)", min_value=1)
            condition = st.selectbox("Condition", ['New', 'Gently Used', 'Used', 'Very Worn'])
        with col2:
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            desc  = st.text_area("Description")
        
        if st.form_submit_button("List Item"):
            if brand and title:
                urls = []
                if files:
                    for f in files:
                        try:
                            img = Image.open(f)
                            if img.mode != 'RGB': img = img.convert('RGB')
                            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, format='JPEG', quality=82)
                            fname = f"{uuid.uuid4()}.jpg"
                            s3_client.put_object(Bucket=S3_BUCKET, Key=fname, Body=buf.getvalue(), ContentType='image/jpeg')
                            urls.append(f"{url}/storage/v1/object/public/{S3_BUCKET}/{fname}")
                        except Exception as e: st.error(f"Image Error: {e}")
                
                supabase.table("items").insert({
                    "owner_id": ME_ID, "brand": brand, "listing_title": title, 
                    "price": price, "photos": urls, "category": category, 
                    "size": size, "condition": condition, "description": desc
                }).execute()
                st.toast("Item Listed! 🎉"); st.rerun()

elif choice == "Purchases & Sales":
    st.markdown("<h2>HISTORY</h2>", unsafe_allow_html=True)
    res = supabase.table("orders").select("*, items(*)").or_(f"buyer_id.eq.{ME_ID},seller_id.eq.{ME_ID}").execute()
    for o in res.data:
        st.markdown(f"Order #{o['id']} - **{o.get('items',{}).get('listing_title','Deleted Item')}**")
        if o.get('shipping_label_url'): st.markdown(f"[Download Label]({o['shipping_label_url']})")

elif choice == "Profile & Settings":
    st.markdown("<h2>PROFILE</h2>", unsafe_allow_html=True)
    with st.form("p"):
        addr = me_data.get('address') or {}
        st1 = st.text_input("Street", value=addr.get('street1',''))
        cty = st.text_input("City", value=addr.get('city',''))
        st_ = st.text_input("State", value=addr.get('state',''))
        zip_ = st.text_input("Zip", value=addr.get('zip',''))
        if st.form_submit_button("Save"):
            supabase.table("users").update({"address": {"street1":st1, "city":cty, "state":st_, "zip":zip_}}).eq("id", ME_ID).execute()
            st.toast("Saved!")
