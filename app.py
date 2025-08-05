import os
import requests
import streamlit as st

# ----------------- Config -----------------
st.set_page_config(page_title="Insurance Assistant", page_icon="🚗", layout="wide")

API_BASE = os.getenv("API_BASE", "https://carinsure-bot.onrender.com").rstrip("/")

# ----------------- Custom Styling -----------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rubik', sans-serif;
        background-color: #f9fbfd;
        color: #333;
    }

     /* Buttons */
    .stButton>button {
        background-color: #e6f2ff !important;
        color: #004080 !important;
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        font-weight: 500;
    }

    /* Quick question buttons */
    .quick-btn button {
        width: 100%;
        background-color: #f1f6ff !important;
        color: #004080 !important;
        font-size: 0.9rem;
        border-radius: 6px;
        padding: 0.4rem;
    }

    /* Chat content */
    .stChatMessageContent {
        font-family: 'Rubik', sans-serif;
        font-size: 0.95rem;
    }

    /* Input fields */
    .stTextInput>div>div>input {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ----------------- Session State -----------------
if "user_registered" not in st.session_state:
    st.session_state.user_registered = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "car" not in st.session_state:
    st.session_state.car = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "greeted" not in st.session_state:
    st.session_state.greeted = False

# ----------------- API Helpers -----------------
def api_register(name: str, email: str, car: str):
    payload = {"name": name, "email": email, "car": car}
    r = requests.post(f"{API_BASE}/register", json=payload, timeout=60)
    r.raise_for_status()
    return r.json() if r.content else {}

def api_history(email: str):
    r = requests.get(f"{API_BASE}/history/{email}", timeout=60)
    r.raise_for_status()
    return r.json() if r.content else {}

def api_ask(email: str, message: str):
    payload = {"email": email, "message": message}
    r = requests.post(f"{API_BASE}/ask", json=payload, timeout=120)
    r.raise_for_status()
    return r.json() if r.content else {}

# ----------------- Registration -----------------
if not st.session_state.user_registered:
    with st.form("user_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            name = st.text_input("Name", placeholder="John Doe")
        with col2:
            email = st.text_input("Email", placeholder="you@email.com")
        with col3:
            car = st.text_input("Car", placeholder="Toyota Corolla")
        submitted = st.form_submit_button("Start Chat")

    if submitted:
        if not name or not email or not car:
            st.warning("Please complete all fields.")
            st.stop()
        try:
            api_register(name, email, car)
        except requests.HTTPError as http_err:
            st.error(f"Registration failed: {http_err.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Registration failed: {e}")
            st.stop()

        st.session_state.user_registered = True
        st.session_state.user_name = name
        st.session_state.user_email = email
        st.session_state.car = car

        try:
            data = api_history(email)
            st.session_state.chat_history = data.get("history", []) if isinstance(data, dict) else []
        except Exception as e:
            st.warning(f"Could not load history: {e}")

        st.rerun()
    else:
        st.stop()

# ----------------- Greeting -----------------
if st.session_state.user_registered and not st.session_state.greeted:
    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(f"Hi {st.session_state.user_name}, nice to meet you! How can I help you today?")
    st.session_state.greeted = True

# ----------------- Quick Questions -----------------
cols = st.columns(3)
quick = None
if cols[0].button("📄 Coverage?", key="cover", help="What does this policy cover?", use_container_width=True):
    quick = "What does this policy cover?"
if cols[1].button("⚠️ Exclusions?", key="exclude", help="What are the exclusions?", use_container_width=True):
    quick = "What are the exclusions in this policy?"
if cols[2].button("❓ Claim Process?", key="claim", help="How to make a claim?", use_container_width=True):
    quick = "How do I make a claim under this policy?"

# ----------------- Chat Input -----------------
query = st.chat_input("Type your question...")
if quick and not query:
    query = quick

# ----------------- Chat Logic -----------------
if query:
    with st.chat_message("user", avatar="👤"):
        st.markdown(query)
    st.session_state.chat_history.append({"role": "user", "message": query})

    answer = ""
    try:
        resp = api_ask(st.session_state.user_email, query)
        answer = (resp.get("answer") or "").strip()
    except requests.HTTPError as http_err:
        answer = f"Server error: {http_err.response.text}"
    except Exception as e:
        answer = f"Error contacting server: {e}"

    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(answer if answer else "_No answer returned_")
    st.session_state.chat_history.append({"role": "assistant", "message": answer})

# ----------------- History -----------------
for msg in st.session_state.chat_history:
    role = msg.get("role", "assistant")
    text = msg.get("message", "")
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(text)
    else:
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown(text)
