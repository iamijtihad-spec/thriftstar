import streamlit as st
import pandas as pd
import braintree
import boto3
import os
import uuid
import requests
import json
import base64
from dotenv import load_dotenv
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
URI_BAD    = get_data_uri("sketch_bad_actor_2.png")
URI_DOME   = get_data_uri("sketch_no_dome_2.png")
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


# --- PREMIUM UI DESIGN SYSTEM --# --- PREMIUM UI DESIGN SYSTEM ---
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
/* Base */
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

/* Sidebar (Clean Mini) */
[data-testid="stSidebar"] {
    background: #F7F7F7 !important;
    border-right: 1px solid #EAEAEA !important;
}
[data-testid="stSidebar"] * { color: #1A1A1C !important; }
[data-testid="stSidebarNav"] { padding-top: 1rem !important; }
[data-testid="stSidebar"] hr { border-color: #EAEAEA !important; }

/* Global Spinner Polish */
[data-testid="stSpinner"] {
    display: flex;
    justify-content: center;
    padding: 2rem;
}
[data-testid="stSpinner"] > div { border-top-color: #F5A623 !important; }
}

/* Headings */
h1 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 2.8rem !important;
    letter-spacing: 3px !important;
    color: #F5A623 !important;
}
h2 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 2px !important;
    color: #1A1A1C !important;
}
h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    color: #1A1A1C !important;
}
p, li, label, span { color: #666 !important; }

/* Cards (st.container with border) */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: #FFFFFF !important;
    border: 1px solid #EAEAEA !important;
    border-radius: 14px !important;
    padding: 1rem !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.03) !important;
    transition: border-color 0.25s, box-shadow 0.25s !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    border-color: #F5A623 !important;
    box-shadow: 0 0 18px rgba(245, 166, 35, 0.18) !important;
}

/* Buttons */
.stButton > button {
    background: #FFFFFF !important;
    color: #1A1A1C !important;
    border: 1px solid #EAEAEA !important;
    border-radius: 999px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    padding: 0.45rem 1.2rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover {
    background: #F5A623 !important;
    color: #0D0D0F !important;
    border-color: #F5A623 !important;
    box-shadow: 0 4px 20px rgba(245,166,35,0.35) !important;
    transform: translateY(-1px) !important;
}
/* Primary buttons */
.stButton > button[kind="primary"] {
    background: #F5A623 !important;
    color: #0D0D0F !important;
    border-color: #F5A623 !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #FFB83E !important;
    box-shadow: 0 6px 24px rgba(245,166,35,0.5) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    background: #1A1A1C !important;
    color: #F0F0F0 !important;
    border: 1px solid #2A2A30 !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #F5A623 !important;
    box-shadow: 0 0 0 2px rgba(245,166,35,0.2) !important;
}
.stSelectbox > div > div { color: #F0F0F0 !important; }
.stSelectbox svg { fill: #F5A623 !important; }
[data-baseweb="popover"] { background: #1A1A1C !important; border: 1px solid #2A2A30 !important; }
[role="option"] { color: #F0F0F0 !important; background: #1A1A1C !important; }
[role="option"]:hover { background: #2A2A30 !important; }

/* Labels */
.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stSelectbox label,
.stRadio label {
    color: #888 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}

/* Radio buttons */
.stRadio div[role="radiogroup"] { gap: 0.4rem !important; }

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 3px !important;
    background: rgba(26,26,28,0.9) !important;
}

/* Divider */
hr { border-color: #2A2A30 !important; }

/* Expander */
details {
    background: #111114 !important;
    border: 1px solid #2A2A30 !important;
    border-radius: 10px !important;
    padding: 0.5rem 1rem !important;
}
details summary {
    color: #F5A623 !important;
    font-weight: 600 !important;
}

/* Spinner */
[data-testid="stSpinner"] > div { border-top-color: #F5A623 !important; }

/* Metric */
[data-testid="stMetric"] label { color: #888 !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #F5A623 !important;
    font-family: 'Bebas Neue' !important;
    font-size: 2rem !important;
}

/* Images */
[data-testid="stImage"] img { border-radius: 10px !important; }

/* Form submit button */
.stForm [data-testid="stFormSubmitButton"] > button {
    background: #F5A623 !important;
    color: #0D0D0F !important;
    border-color: #F5A623 !important;
    font-weight: 700 !important;
    width: 100% !important;
}

/* Caption */
.stCaption { color: #666 !important; font-size: 0.75rem !important; }

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: #1A1A1C !important;
    border: 1px dashed #2A2A30 !important;
    border-radius: 10px !important;
}

/* Grailed-style item cards */
.grailed-card {
    position: relative;
    background: #FFFFFF;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #EAEAEA;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
    margin-bottom: 1rem;
}
.grailed-card:hover {
    transform: translateY(-4px);
    border-color: #F5A623;
    box-shadow: 0 8px 30px rgba(245,166,35,0.2);
}
.grailed-card img {
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    display: block;
    border-radius: 0;
}
.grailed-card .card-info { padding: 0.6rem 0.75rem 0.75rem; }
.grailed-card .card-brand {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    letter-spacing: 1.5px;
    color: #1A1A1C;
    line-height: 1.1;
}
.grailed-card .card-title {
    font-size: 0.75rem;
    color: #888;
    margin: 0.15rem 0 0.4rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.grailed-card .card-price {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    color: #F5A623;
    letter-spacing: 1px;
}

/* Hero graphic (login wall) */
.hero-graphic {
    display: flex;
    justify-content: center;
    margin: 0.5rem 0 1.5rem;
    transition: transform 0.3s ease;
}
.hero-graphic img {
    max-width: 320px;
    filter: drop-shadow(0 0 12px rgba(0,0,0,0.05));
    transition: filter 0.3s ease, transform 0.3s ease;
}
.hero-graphic:hover img {
    filter: drop-shadow(0 0 24px rgba(245,166,35,0.25));
    transform: scale(1.03);
}

/* Empty state */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 2.5rem 1rem;
    color: #555;
}
.empty-state img {
    max-width: 140px;
    margin-bottom: 1rem;
    opacity: 0.6;
}
.empty-state h3 { color: #888 !important; font-size: 1rem !important; }
.empty-state p  { color: #AAA !important; font-size: 0.85rem !important; }

/* Burger / lighter divider */
.burger-divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0.5rem 0;
}
.burger-divider img { height: 28px; opacity: 0.35; }
.burger-divider hr  { flex: 1; border-color: #2A2A30; margin: 0; }

/* Kill column padding for dense grid */
[data-testid="column"] { padding: 0 6px !important; }

/* iMessage-style DM bubbles */
.dm-thread {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 1rem 0;
}
.dm-bubble {
    max-width: 75%;
    padding: 0.6rem 0.9rem;
    border-radius: 18px;
    font-size: 0.88rem;
    line-height: 1.4;
    word-wrap: break-word;
}
.dm-bubble.sent {
    background: #F5A623;
    color: #0D0D0F !important;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
}
.dm-bubble.received {
    background: #1E1E22;
    color: #F0F0F0 !important;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
    border: 1px solid #2A2A30;
}
.dm-bubble .dm-meta { font-size: 0.7rem; opacity: 0.6; margin-top: 0.25rem; }
.dm-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #111114;
    border-radius: 12px;
    border: 1px solid #2A2A30;
    margin-bottom: 0.5rem;
}
.dm-avatar {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: #F5A623;
    color: #0D0D0F !important;
    font-weight: 700;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.dm-status-pill {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.dm-status-pill.pending  { background: rgba(245,166,35,0.15); color: #F5A623 !important;  border: 1px solid #F5A623; }
.dm-status-pill.accepted { background: rgba(0,200,100,0.15);  color: #00C864 !important;  border: 1px solid #00C864; }
.dm-status-pill.declined { background: rgba(255,60,60,0.15);  color: #FF3C3C !important;  border: 1px solid #FF3C3C; }
</style>
""")


# ==========================================
# SESSION MANAGEMENT
# ==========================================
if 'user'           not in st.session_state: st.session_state.user           = None
if 'access_token'   not in st.session_state: st.session_state.access_token   = None
if 'refresh_token'  not in st.session_state: st.session_state.refresh_token  = None
if 'checkout_item'  not in st.session_state: st.session_state.checkout_item  = None
if 'view_item'      not in st.session_state: st.session_state.view_item      = None

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

if device_id and st.session_state.user is None:
    sessions = get_persisted_sessions()
    if device_id in sessions:
        tokens = sessions[device_id]
        try:
            res = supabase.auth.set_session(tokens["access_token"], tokens["refresh_token"])
            if res.user:
                st.session_state.user         = res.user
                st.session_state.access_token = tokens["access_token"]
                st.session_state.refresh_token = tokens["refresh_token"]
        except Exception:
            remove_session(device_id)

if st.session_state.user is not None and st.session_state.access_token is not None:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except Exception:
        pass

def logout():
    try: supabase.auth.sign_out()
    except Exception: pass
    did = st.query_params.get("device")
    if did:
        remove_session(did)
        st.query_params.clear()
    for k in ["user","access_token","refresh_token","checkout_item","view_item"]:
        st.session_state[k] = None


def get_user_by_id(user_id):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def get_braintree_client_token():
    if not braintree_configured:
        return None
    try:
        return gateway.client_token.generate()
    except Exception:
        return None

def process_braintree_transaction(amount, nonce):
    if not braintree_configured:
        return False, "Braintree gateway not configured."
    result = gateway.transaction.sale({
        "amount": f"{amount:.2f}",
        "payment_method_nonce": nonce,
        "options": {"submit_for_settlement": True}
    })
    if result.is_success:
        return True, result.transaction.id
    return False, result.message

def create_shipping_label(sender_id, receiver_id):
    if not shippo_configured:
        return False, "Shippo API key not configured."
    sender   = get_user_by_id(sender_id)
    receiver = get_user_by_id(receiver_id)
    addr_from = sender.get('address')
    addr_to   = receiver.get('address')
    if not addr_from or not addr_from.get('street1'):
        return False, "Missing Sender Address."
    if not addr_to or not addr_to.get('street1'):
        return False, "Missing Receiver Address."
    addr_from["email"] = sender.get("email", "support@thriftstar.app")
    addr_from["phone"] = addr_from.get("phone", "5555555555")
    addr_to["email"]   = receiver.get("email", "support@thriftstar.app")
    addr_to["phone"]   = addr_to.get("phone", "5555555555")
    headers = {"Authorization": f"ShippoToken {SHIPPO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "address_from": addr_from, "address_to": addr_to,
        "parcels": [{"length":"12","width":"10","height":"4","distance_unit":"in","weight":"2","mass_unit":"lb"}],
        "async": False
    }
    try:
        response = requests.post("https://api.goshippo.com/shipments/", json=payload, headers=headers).json()
        if "rates" in response and len(response["rates"]) > 0:
            rate_id = response["rates"][0]["object_id"]
            txn = requests.post("https://api.goshippo.com/transactions/", json={"rate": rate_id, "async": False}, headers=headers).json()
            if txn.get("status") == "SUCCESS":
                return True, txn.get("label_url")
            return False, "Shippo Transaction Error."
        return False, "Shippo Rates Error."
    except Exception as e:
        return False, f"Shippo Exception: {e}"


# ==========================================
# 🛑 LOGIN / SIGN UP WALL
# ==========================================
if st.session_state.user is None:
    st.markdown(
        "<h1 style='text-align:center;letter-spacing:6px;color:#F5A623;margin-bottom:0;'>⭐ THRIFT STAR</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center;color:#555;font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;margin-top:0;'>Buy · Sell · Swap Streetwear</p>",
        unsafe_allow_html=True
    )
    if URI_VEND:
        st.markdown(
            f'<div class="hero-graphic"><img src="{URI_VEND}" alt="Thrift Star Vending Machine"></div>',
            unsafe_allow_html=True
        )
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Login")
            email_login    = st.text_input("Email", key="login_email")
            password_login = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": password_login})
                    st.session_state.user          = res.user
                    st.session_state.access_token  = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    new_device_id = str(uuid.uuid4())
                    st.query_params["device"] = new_device_id
                    save_session(new_device_id, res.session.access_token, res.session.refresh_token)
                    st.rerun()
                except Exception:
                    st.error("Login Failed: Please check your credentials.")
    with col2:
        with st.container(border=True):
            st.subheader("Create Account")
            username_signup = st.text_input("Desired Username")
            email_signup    = st.text_input("Email", key="signup_email")
            password_signup = st.text_input("Password", type="password", key="signup_password")
            if st.button("Sign Up"):
                if username_signup and email_signup and password_signup:
                    try:
                        res = supabase.auth.sign_up({"email": email_signup, "password": password_signup})
                        if res.user and res.session:
                            st.session_state.user          = res.user
                            st.session_state.access_token  = res.session.access_token
                            st.session_state.refresh_token = res.session.refresh_token
                            new_device_id = str(uuid.uuid4())
                            st.query_params["device"] = new_device_id
                            save_session(new_device_id, res.session.access_token, res.session.refresh_token)
                            supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
                            supabase.table("users").insert({
                                "id": res.user.id, "username": username_signup, "email": email_signup
                            }).execute()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Sign Up Failed: {e}")
                else:
                    st.error("Please fill out all fields.")
    st.stop()


# ==========================================
# ✅ MAIN THRIFT STAR APP (LOGGED IN)
# ==========================================
ME_ID   = st.session_state.user.id
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
    return supabase.table("cart_items").select("*, items!inner(*, users!inner(username))").eq("user_id", ME_ID).execute().data

# Main header
st.title("⭐ Thrift Star")
st.markdown("*The premier marketplace for thrifters to buy, sell, and **SWAP**.*")

# Sidebar
with st.sidebar:
    st.divider()
    if URI_VEND:
        st.sidebar.markdown(
            f'<div style="text-align:center;"><img src="{URI_VEND}" style="width:110px; opacity:0.9; margin-bottom:0.8rem;"/></div>',
            unsafe_allow_html=True
        )
    st.divider()
    # Side art removed (as per user request: 'remove tacky sidebar sketches')
    pass

menu   = ["Home Feed", "Shopping Cart", "Negotiations & Offers", "My Closet", "Purchases & Sales", "Profile & Settings"]
choice = st.sidebar.radio("Navigation", menu)
st.sidebar.divider()
st.sidebar.markdown(f"**🟢 Online as:** `{ME_NAME}`")
st.sidebar.button("Log Out", on_click=logout)


# ==========================================
# DYNAMIC ROUTING COMPONENTS
# ==========================================
def render_isolated_item_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(view_item=None))
    burger_divider()
    colA, colB = st.columns([1, 1])
    with colA:
        if item.get('photos') and len(item['photos']) > 0:
            for i, p_url in enumerate(item['photos']):
                st.image(p_url, use_container_width=True, caption=f"Photo {i+1}")
        else:
            st.image("https://placehold.co/600x600/1A1A1C/333?text=No+Image", use_container_width=True)
    with colB:
        st.subheader(f"{item['brand']} {item['listing_title']}")
        seller = get_user_by_id(item['owner_id'])
        st.markdown(f"**Seller:** {seller['username'] if seller else 'Unknown'}")
        st.markdown(f"**Size:** {item.get('size','N/A')} | **Condition:** {item.get('condition','N/A')}")
        st.markdown(f"**Price:** ${item['price']}")
        st.write("**Description:**")
        st.write(item.get('description', ''))
        st.divider()
        if item['owner_id'] != ME_ID and item['status'] == 'Available':
            act_cols = st.columns(2)
            with act_cols[0]:
                if st.button("Add to Cart", key=f"isocart_{item['id']}"):
                    try:
                        supabase.table("cart_items").insert({"user_id": ME_ID, "item_id": item['id']}).execute()
                        st.toast("Added to cart!")
                    except:
                        st.toast("Already in cart.")
            with act_cols[1]:
                if st.button("Buy Now", key=f"isobuy_{item['id']}", type="primary"):
                    st.session_state.checkout_item = item
                    st.session_state.view_item     = None
                    st.rerun()
            with st.expander("🤝 Propose a Swap"):
                my_items = get_my_items()
                if not my_items:
                    st.warning("Your closet is empty!")
                else:
                    item_options   = {i["listing_title"]: i for i in my_items}
                    offer_item_name = st.selectbox("Select from your closet:", list(item_options.keys()), key=f"isoselect_{item['id']}")
                    cash_boot       = st.number_input("Cash boot ($)?", min_value=0, value=0, step=10, key=f"isocash_{item['id']}")
                    if st.button("Send Offer", key=f"isobtn_{item['id']}"):
                        offered_item = item_options[offer_item_name]
                        supabase.table("swap_proposals").insert({
                            "original_proposer_id": ME_ID,
                            "original_receiver_id": item["owner_id"],
                            "item_wanted_id":        item["id"],
                            "item_offered_id":       offered_item["id"],
                            "cash_added":            cash_boot,
                            "status":                "Pending",
                            "action_with_id":        item["owner_id"]
                        }).execute()
                        st.toast("Swap offer sent! 🤝")

def render_checkout_page(item):
    st.button("← Back", on_click=lambda: st.session_state.update(checkout_item=None))
    burger_divider()
    st.subheader("Secure Checkout Tracker")
    col1, col2 = st.columns(2)
    with col1:
        st.image(item['photos'][0] if item.get('photos') else "https://placehold.co/400", width=250)
        st.markdown(f"**{item['brand']} {item['listing_title']}**")
        seller = get_user_by_id(item['owner_id'])
        st.caption(f"Seller: {seller['username'] if seller else 'Unknown'}")
        if seller and seller.get('paypal_email'):
            st.success("✅ Seller has a linked PayPal Account.")
        else:
            st.warning("⚠️ Seller has no PayPal. Escrow hold applied.")
    with col2:
        with st.container(border=True):
            subtotal = float(item['price'])
            app_fee  = round(subtotal * 0.10, 2)
            total    = subtotal + app_fee
            st.markdown("### Order Summary")
            st.markdown(f"Subtotal: **${subtotal:.2f}**")
            st.markdown(f"ThriftStar Fee (10%): **${app_fee:.2f}**")
            st.divider()
            st.markdown(f"## Total: ${total:.2f}")
            method = st.radio("Payment Method", ["PayPal / Credit Card"])
            
            # --- BRAINTREE DROP-IN INTEGRATION ---
            token = get_braintree_client_token()
            if not token:
                st.error("Payment Gateway unreachable. Please try again later.")
            else:
                # Capture nonce from Query Params (Set by JS below)
                captured_nonce = st.query_params.get("payment_nonce")
                
                if captured_nonce:
                    st.success("✅ Payment Method Verified. Click 'Complete Purchase' below.")
                    if st.button("Complete Purchase", type="primary"):
                        addr = me_data.get('address')
                        if not addr or not addr.get("street1"):
                            st.error("Please add a Shipping Address in Profile & Settings first!")
                        else:
                            with st.spinner("Finalizing Order..."):
                                success, txn = process_braintree_transaction(total, captured_nonce)
                                if success:
                                    # Cleanup nonce from URL after use
                                    st.query_params.clear()
                                    supabase.table("orders").insert({
                                        "buyer_id":        ME_ID,
                                        "seller_id":       item["owner_id"],
                                        "item_id":         item["id"],
                                        "amount":          total,
                                        "braintree_txn_id": txn
                                    }).execute()
                                    supabase.table("items").update({"status": "Sold"}).eq("id", item["id"]).execute()
                                    supabase.table("cart_items").delete().eq("item_id", item["id"]).execute()
                                    st.success("HUSTLE SUCCESSFUL! Order placed. 🛍️")
                                    st.session_state.checkout_item = None
                                    st.rerun()
                                else:
                                    st.error(f"Transaction Error: {txn}")
                else:
                    # Render Drop-in UI
                    from streamlit.components.v1 import html as st_html
                    dropin_html = f"""
                    <script src="https://js.braintreegateway.com/web/dropin/1.42.0/js/dropin.min.js"></script>
                    <div id="dropin-container"></div>
                    <button id="submit-button" style="background:#F5A623; color:white; border:none; padding:10px 20px; border-radius:20px; font-family:sans-serif; cursor:pointer; width:100%; font-weight:bold; margin-top:10px;">VERIFY PAYMENT METHOD</button>
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
                                    // Hack: Post nonce back to parent via URL
                                    const url = new URL(window.parent.location.href);
                                    url.searchParams.set('payment_nonce', payload.nonce);
                                    window.parent.location.href = url.href;
                                }});
                            }});
                        }});
                    </script>
                    """
                    st_html(dropin_html, height=450)
                    st.caption("Verify your PayPal or Card above to enable 'Complete Purchase'.")

if st.session_state.view_item is not None:
    render_isolated_item_page(st.session_state.view_item)
    st.stop()

if st.session_state.checkout_item is not None:
    render_checkout_page(st.session_state.checkout_item)
    st.stop()


# ==========================================
# PAGE ROUTING
# ==========================================

# ---- HOME FEED ----
if choice == "Home Feed":
    hcol1, hcol2 = st.columns([8, 1])
    with hcol1:
        st.markdown("<h2 style='margin-bottom:0;'>DISCOVER STEALS</h2>", unsafe_allow_html=True)
    with hcol2:
        # Lighter sketch removed (as per user request)
        pass
    feed = get_feed_items()
    if not feed:
        empty_state(URI_SHOE, "The feed is empty.", "Be the first to list some heat. 👟")
    else:
        cols = st.columns(4)
        for index, item in enumerate(feed):
            with cols[index % 4]:
                image_url = item['photos'][0] if item.get('photos') and len(item['photos']) > 0 else "https://placehold.co/400x400/1A1A1C/555?text=NO+IMAGE"
                brand  = item.get('brand', 'UNKNOWN').upper()
                name   = item.get('listing_title', 'Item')
                size   = item.get('size', 'OS')
                price  = item.get('price', 0)
                seller = item.get('users', {}).get('username', 'Unknown') if isinstance(item.get('users'), dict) else 'Unknown'
                st.markdown(f"""
                <div class="grailed-card">
                    <img src="{image_url}" alt="{brand}">
                    <div class="card-info">
                        <div class="card-brand">{brand}</div>
                        <div class="card-title">{name}</div>
                        <div class="grailed-meta" style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:0.72rem;color:#666;">{size} &bull; {seller}</span>
                            <span class="card-price">${price}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Cart", key=f"cart_{item['id']}", help="Add to cart"):
                        try:
                            supabase.table("cart_items").insert({"user_id": ME_ID, "item_id": item['id']}).execute()
                            st.toast(f"Added {brand} to cart!")
                        except:
                            st.toast("Already in cart.")
                with c2:
                    if st.button("View", key=f"view_{item['id']}", help="View details"):
                        st.session_state.view_item = item
                        st.rerun()
                with st.expander("🤝 Swap"):
                    my_items = get_my_items()
                    if not my_items:
                        st.caption("Your closet is empty.")
                    else:
                        item_options = {i["listing_title"]: i for i in my_items}
                        offer_name   = st.selectbox("Offer:", list(item_options.keys()), key=f"sel_{item['id']}", label_visibility="collapsed")
                        cash_boot    = st.number_input("+ Cash ($)", min_value=0, value=0, step=5, key=f"cash_{item['id']}")
                        if st.button("Send Offer", key=f"btn_{item['id']}", type="primary"):
                            offered = item_options[offer_name]
                            supabase.table("swap_proposals").insert({
                                "original_proposer_id": ME_ID,
                                "original_receiver_id": item["owner_id"],
                                "item_offered_id":      offered["id"],
                                "item_wanted_id":       item["id"],
                                "cash_added":           cash_boot,
                                "status":               "Pending",
                                "action_with_id":       item["owner_id"]
                            }).execute()
                            st.toast("Swap offer sent! 🤝")


# ---- SHOPPING CART ----
elif choice == "Shopping Cart":
    st.markdown("<h2>YOUR CART</h2>", unsafe_allow_html=True)
    cart_items = get_cart_items()
    if not cart_items:
        empty_state(URI_WOOF, "Woof! Your cart is empty.", "Go to the feed and add some steals.")
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
                    if st.button("Remove", key=f"rm_cart_{c['id']}"):
                        supabase.table("cart_items").delete().eq("id", c['id']).execute()
                        st.rerun()
        burger_divider()
        app_fee    = round(subtotal_price * 0.10, 2)
        total_price = subtotal_price + app_fee
        st.markdown(f"**Subtotal:** ${subtotal_price:.2f} | **ThriftStar Fee (10%):** ${app_fee:.2f}")
        st.markdown(f"## Total: ${total_price:.2f}")
        st.radio("Payment Method", ["PayPal Dashboard", "Credit Card"])
        if st.button("Confirm Checkout", type="primary"):
            addr = me_data.get('address')
            if not addr or not addr.get("street1"):
                st.error("Please add a Shipping Address in Profile & Settings before checking out.")
            else:
                with st.spinner("Authorizing..."):
                    success, txn = process_braintree_transaction(total_price, "fake-valid-nonce")
                    if success:
                        for c in cart_items:
                            item = c['items']
                            supabase.table("orders").insert({
                                "buyer_id":        ME_ID,
                                "seller_id":       item["owner_id"],
                                "item_id":         item["id"],
                                "amount":          item["price"] * 1.10,
                                "braintree_txn_id": txn
                            }).execute()
                            supabase.table("items").update({"status": "Sold"}).eq("id", item["id"]).execute()
                            supabase.table("cart_items").delete().eq("id", c['id']).execute()
                        st.toast("Checkout Successful! 🎉")
                        st.rerun()
                    else:
                        st.error(f"Checkout Failed: {txn}")


# ---- NEGOTIATIONS & OFFERS ----
elif choice == "Negotiations & Offers":
    hc1, hc2 = st.columns([6, 1])
    with hc1:
        st.markdown("<h2 style='margin-bottom:0;'>NEGOTIATIONS & OFFERS</h2>", unsafe_allow_html=True)
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
            is_cash_offer = p["item_offered_id"] is None
            their_item_id = p["item_wanted_id"] if am_i_proposer else p["item_offered_id"]
            their_item    = get_item_by_id(their_item_id) if their_item_id else None
            other_user    = get_user_by_id(other_user_id)
            other_username = other_user["username"] if other_user else "Unknown"
            status        = p["status"]
            status_class  = {"Accepted": "accepted", "Declined": "declined"}.get(status, "pending")
            offer_type    = "💵 Cash Offer" if is_cash_offer else "🔄 Item Swap"

            # DM-style header
            st.markdown(f"""
            <div class="dm-header">
                <div class="dm-avatar">{other_username[0].upper()}</div>
                <div style="flex:1;">
                    <div style="font-weight:700;font-size:0.95rem;">{other_username}</div>
                    <div style="font-size:0.75rem;color:#666;">{offer_type}</div>
                </div>
                <span class="dm-status-pill {status_class}">{status}</span>
            </div>
            """, unsafe_allow_html=True)

            # Bubble thread
            if is_cash_offer and their_item:
                bubble_text = f"Offered <strong>${p['cash_added']}</strong> for <strong>{their_item['brand']} {their_item['listing_title']}</strong>"
                side = "sent" if am_i_proposer else "received"
                st.markdown(f"""
                <div class="dm-thread">
                    <div class="dm-bubble {side}">{bubble_text}
                        <div class="dm-meta">{'You' if am_i_proposer else other_username}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            elif their_item:
                my_item = get_item_by_id(p["item_offered_id"] if am_i_proposer else p["item_wanted_id"])
                bubble_sent = f"Offering <strong>{my_item['brand'] if my_item else '?'}</strong>" + (f" + ${p['cash_added']}" if p.get('cash_added') else "")
                bubble_recv = f"for <strong>{their_item['brand']} {their_item['listing_title']}</strong>"
                side = "sent" if am_i_proposer else "received"
                st.markdown(f"""
                <div class="dm-thread">
                    <div class="dm-bubble {side}">{bubble_sent}<br>{bubble_recv}
                        <div class="dm-meta">{'You' if am_i_proposer else other_username}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

            # Action area
            if status == "Accepted":
                st.success("✅ Deal closed! Generate your shipping labels below.")
                if st.button("Generate Shipping Label", key=f"sship_{p['id']}"):
                    s1, err = create_shipping_label(ME_ID, other_user_id)
                    if s1: st.markdown(f"📥 **[Download Label → {other_username}]({err})**")
                    else:  st.error(err)
            elif status == "Declined":
                st.error("❌ This offer was declined.")
            else:
                if p["action_with_id"] != ME_ID:
                    st.caption("Waiting for their response...")
                else:
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        st.number_input("Counter-offer ($)", min_value=0,
                                        value=int(p.get('cash_added') or 0),
                                        step=5, key=f"counter_{p['id']}")
                    with col_b:
                        if st.button("Accept", key=f"acc_{p['id']}", type="primary"):
                            addr = me_data.get('address')
                            if not addr or not addr.get('street1'):
                                st.error("Add Shipping Address in Settings first!")
                            else:
                                update_payload    = {"status": "Accepted", "action_with_id": None}
                                payment_successful = True
                                if p.get('cash_added', 0) > 0:
                                    pay_success, pay_result = process_braintree_transaction(float(p['cash_added']), "fake-valid-nonce")
                                    if pay_success:
                                        update_payload["braintree_txn_id"] = pay_result
                                    else:
                                        st.error(f"Payment Failed: {pay_result}")
                                        payment_successful = False
                                if payment_successful:
                                    supabase.table("swap_proposals").update(update_payload).eq("id", p["id"]).execute()
                                    if is_cash_offer:
                                        supabase.table("orders").insert({
                                            "buyer_id":        p["original_proposer_id"],
                                            "seller_id":       p["original_receiver_id"],
                                            "item_id":         p["item_wanted_id"],
                                            "amount":          p["cash_added"],
                                            "braintree_txn_id": update_payload.get("braintree_txn_id", "Cash-Offer")
                                        }).execute()
                                        supabase.table("items").update({"status": "Sold"}).eq("id", p["item_wanted_id"]).execute()
                                    else:
                                        # Leg A: Proposer receives Receiver's item
                                        supabase.table("orders").insert({
                                            "buyer_id":        p["original_proposer_id"],
                                            "seller_id":       p["original_receiver_id"],
                                            "item_id":         p["item_wanted_id"],
                                            "amount":          p.get("cash_added", 0),
                                            "braintree_txn_id": update_payload.get("braintree_txn_id", "Swap-Leg-A")
                                        }).execute()
                                        # Leg B: Receiver gets Proposer's item
                                        supabase.table("orders").insert({
                                            "buyer_id":        p["original_receiver_id"],
                                            "seller_id":       p["original_proposer_id"],
                                            "item_id":         p["item_offered_id"],
                                            "amount":          0,
                                            "braintree_txn_id": "Swap-Leg-B"
                                        }).execute()
                                        supabase.table("items").update({"status": "Swapped"}).eq("id", p["item_wanted_id"]).execute()
                                        supabase.table("items").update({"status": "Swapped"}).eq("id", p["item_offered_id"]).execute()
                                    st.toast("Deal done! 🤝 Generate your shipping labels.")
                                    st.rerun()
                    with col_c:
                        if st.button("Decline", key=f"dec_{p['id']}"):
                            supabase.table("swap_proposals").update({"status": "Declined"}).eq("id", p["id"]).execute()
                            st.toast("Offer declined.")
                            st.rerun()
            st.divider()


# ---- MY CLOSET ----
elif choice == "My Closet":
    st.markdown("<h2>MY CLOSET</h2>", unsafe_allow_html=True)
    my_items = get_my_items()
    if not my_items:
        empty_state(URI_VEND, "Your closet is bare.", "List some items to start swapping.")
    else:
        closet_cols = st.columns(4)
        for index, item in enumerate(my_items):
            with closet_cols[index % 4]:
                image_url = item['photos'][0] if item.get('photos') and len(item['photos']) > 0 else "https://placehold.co/400x400/1A1A1C/555?text=NO+IMAGE"
                status_color = {"Available": "#00C864", "Sold": "#FF3C3C", "Swapped": "#F5A623"}.get(item.get('status',''), '#888')
                st.markdown(f"""
                <div class="grailed-card">
                    <img src="{image_url}" alt="{item['brand']}">
                    <div class="card-info">
                        <div class="card-brand">{item['brand'].upper()}</div>
                        <div class="card-title">{item['listing_title']}</div>
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span class="card-price">${item['price']}</span>
                            <span style="font-size:0.7rem;color:{status_color};">{item.get('status','')}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("View / Edit", key=f"cview_{item['id']}"):
                    st.session_state.view_item = item
                    st.rerun()

    burger_divider()
    st.markdown("<h2>ADD NEW ITEM</h2>", unsafe_allow_html=True)
    with st.form("add_item"):
        col1, col2 = st.columns(2)
        with col1:
            brand     = st.text_input("Brand")
            name      = st.text_input("Listing Title")
            category  = st.selectbox("Category", ["Tops", "Bottoms", "Outerwear", "Sneakers", "Accessories", "Other"])
            size      = st.text_input("Size")
            price     = st.number_input("Estimated Value ($)", min_value=1.0)
            condition = st.selectbox("Condition", ['New', 'Gently Used', 'Used', 'Very Worn'])
        with col2:
            uploaded_files = st.file_uploader("Upload Photos (Max 5)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            desc = st.text_area("Description")
        if st.form_submit_button("List Item"):
            if brand and name:
                image_urls = []
                if uploaded_files:
                    for f in uploaded_files:
                        ext   = f.name.split(".")[-1]
                        fname = f"{uuid.uuid4()}.{ext}"
                        try:
                            s3_client.put_object(
                                Bucket=S3_BUCKET, Key=fname,
                                Body=f.getvalue(),
                                ContentType=f.type
                            )
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
                        st.toast("Item listed! 🎉")
                        st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")


# ---- PURCHASES & SALES ----
elif choice == "Purchases & Sales":
    st.markdown("<h2>ORDER HISTORY & SHIPPING</h2>", unsafe_allow_html=True)
    orders_res = supabase.table("orders") \
        .select("*, items!inner(*), buyer:users!orders_buyer_id_fkey(*), seller:users!orders_seller_id_fkey(*)") \
        .or_(f"buyer_id.eq.{ME_ID},seller_id.eq.{ME_ID}") \
        .order("created_at", desc=True).execute()
    orders = orders_res.data
    if not orders:
        empty_state(URI_VEND, "No sales or purchases yet.", "Time to get hustling.")
    else:
        for o in orders:
            item       = o['items']
            im_buyer   = o['buyer_id'] == ME_ID
            role       = "BUYER" if im_buyer else "SELLER"
            other_name = o['seller']['username'] if im_buyer else o['buyer']['username']
            with st.container(border=True):
                st.markdown(f"**[{role}]** {item['brand']} {item['listing_title']} — **${o['amount']}**")
                st.caption(f"Order ID: {o['id']} | Txn: {o.get('braintree_txn_id','')}")
                if st.button("Generate Shipping Label", key=f"label_{o['id']}"):
                    with st.spinner("Generating USPS Label..."):
                        success, label_or_err = create_shipping_label(o['seller']['id'], o['buyer']['id'])
                        if success:
                            st.markdown(f"📥 **[Download USPS Shipping Label PDF]({label_or_err})**")
                        else:
                            st.error(f"Shippo Error: {label_or_err}")


# ---- PROFILE & SETTINGS ----
elif choice == "Profile & Settings":
    st.markdown("<h2>PROFILE & SETTINGS</h2>", unsafe_allow_html=True)
    st.info("Addresses saved here are piped directly to the Shippo Logistics API for all live transactions.")
    burger_divider()
    with st.form("profile_form"):
        st.write("### Public Profile")
        new_name = st.text_input("Full Name",  value=me_data.get('full_name', '') if me_data else '')
        new_bio  = st.text_area("Bio",         value=me_data.get('bio', '')       if me_data else '')

        st.write("### Private Shipping & Contact Details")
        addr = (me_data.get('address') or {}) if me_data else {}
        c1, c2 = st.columns(2)
        with c1:
            street   = st.text_input("Street Address", value=addr.get('street1', ''))
            city     = st.text_input("City",            value=addr.get('city', ''))
        with c2:
            state    = st.text_input("State",           value=addr.get('state', ''))
            zip_code = st.text_input("ZIP Code",        value=addr.get('zip', ''))
        phone      = st.text_input("Phone Number",      value=addr.get('phone', ''))
        new_paypal = st.text_input("PayPal Email (For Payouts)", value=me_data.get('paypal_email', '') if me_data else '')

        if st.form_submit_button("Save Profile"):
            supabase.table("users").update({
                "full_name":    new_name,
                "bio":          new_bio,
                "paypal_email": new_paypal,
                "address": {
                    "street1": street,
                    "city":    city,
                    "state":   state,
                    "zip":     zip_code,
                    "phone":   phone
                }
            }).eq("id", ME_ID).execute()
            st.toast("Profile updated! ✅")
