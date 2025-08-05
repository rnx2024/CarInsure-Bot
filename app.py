import os
import re
import requests
import streamlit as st

# =========================
# Config
# =========================
st.set_page_config(page_title="Insurance Assistant", page_icon="🚗", layout="wide")
API_BASE = os.getenv("API_BASE", "https://carinsure-bot.onrender.com").rstrip("/")
READ_TIMEOUT = 120
CONNECT_TIMEOUT = 60

# =========================
# Global Styles
# =========================
st.markdown("""
    <style>
    body, .stApp {
        background: linear-gradient(120deg, #f8fbff, #e4ecf7);
    }
    .app-shell {
        min-height: calc(100vh - 1.5rem);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .app-card {
        width: 800px;
        max-width: 92vw;
        background-color: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
    }
    .app-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }
    .app-header h2 {
        margin: 0;
        font-weight: 600;
    }
    .stButton>button {
        background-color: #1E40AF !important;
        color: #ffffff !important;
        padding: 0.6rem 1.2rem;
        font-size: 14px !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #2563EB !important;
    }
    .stTextInput>div>div>input, .stTextArea textarea {
        border-radius: 8px;
        font-size: 16px;
    }
    .chat-scroll {
        max-height: 55vh;
        overflow-y: auto;
        padding-right: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# =========================
# Session State
# =========================
ss = st.session_state
ss.setdefault("user_registered", False)
ss.setdefault("user_name", "")
ss.setdefault("user_email", "")
ss.setdefault("user_last_email", "")
ss.setdefault("car", "")
ss.setdefault("chat_history", [])
ss.setdefault("greeted", False)
ss.setdefault("draft_msg", "")   # IMPORTANT: will be cleared after send

# =========================
# Helpers
# =========================
def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))

def api_register(name: str, email: str, car: str):
    r = requests.post(
        f"{API_BASE}/register",
        json={"name": name, "email": email, "car": car},
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    r.raise_for_status()
    return r.json() if r.content else {}

def api_history(email: str):
    r = requests.get(
        f"{API_BASE}/history/{email}",
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    r.raise_for_status()
    return r.json() if r.content else {}

def api_ask(email: str, message: str):
    r = requests.post(
        f"{API_BASE}/ask",
        json={"email": email, "message": message},
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    r.raise_for_status()
    return r.json() if r.content else {}

def render_history_list(history):
    if not history:
        st.info("No history yet.")
        return
    for msg in history:
        role = msg.get("role", "assistant")
        text = msg.get("message", "")
        with st.chat_message("user" if role == "user" else "assistant",
                             avatar=("👤" if role == "user" else "🚗")):
            st.markdown(text)

def logout_reset():
    ss.clear()
    ss["user_registered"] = False
    ss["chat_history"] = []
    ss["greeted"] = False
    ss["draft_msg"] = ""
    st.rerun()

def render_quick_actions():
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📄 Coverage?", help="What does this policy cover?"):
            ss.draft_msg = "What does this policy cover?"
            st.rerun()
    with c2:
        if st.button("⚠️ Exclusions?", help="What are the exclusions?"):
            ss.draft_msg = "What are the exclusions in this policy?"
            st.rerun()
    with c3:
        if st.button("❓ Claim Process?", help="How do I make a claim?"):
            ss.draft_msg = "How do I make a claim under this policy?"
            st.rerun()

def handle_chat_input():
    """Single place where st.chat_input is created and handled."""
    if not ss.user_email:
        return

    # Use explicit placeholder=, and key= binds the current value.
    query = st.chat_input(placeholder="Type your question...", key="draft_msg")

    # If user didn't submit, nothing to do.
    if not query:
        return

    # Echo user's message and persist to history
    with st.chat_message("user", avatar="👤"):
        st.markdown(query)
    ss.chat_history.append({"role": "user", "message": query})

    # Call backend
    try:
        resp = api_ask(ss.user_email, query)
        answer = (resp.get("answer") or "").strip()
    except requests.HTTPError as http_err:
        answer = f"Server error: {http_err.response.text}"
    except Exception as e:
        answer = f"Error contacting server: {e}"

    # Show assistant message and persist
    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(answer if answer else "_No answer returned_")
    ss.chat_history.append({"role": "assistant", "message": answer})

    # CLEAR the input so the placeholder shows again on the next render
    ss.draft_msg = ""
    st.rerun()  # single rerun to refresh the input with placeholder

# =========================
# Registration / Login (Email-first with fallback)
# =========================
if not ss.user_registered:
    st.markdown('<div class="app-shell"><div class="app-card">', unsafe_allow_html=True)
    st.markdown("""
        <div class="app-header">
            <span style="font-size: 24px;">🚗</span>
            <h2>Insurance Assistant</h2>
        </div>
    """, unsafe_allow_html=True)

    with st.form("email_first_form", clear_on_submit=False):
        email = st.text_input("Email", value=ss.get("user_last_email", ""), placeholder="you@email.com")
        email_submit = st.form_submit_button("Continue", use_container_width=True)
    if email_submit and is_valid_email(email):
        try:
            data = api_history(email)
            ss.user_email = email
            ss.user_last_email = email
            ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
            ss.user_registered = True
            st.rerun()
        except requests.HTTPError:
            pass
        except Exception as e:
            st.warning(f"Could not verify email: {e}")

    if not ss.user_registered:
        st.markdown("---")
        with st.form("user_form", clear_on_submit=False):
            name = st.text_input("Name", placeholder="John Doe")
            new_email = st.text_input("Confirm Email", value=email or "", placeholder="you@email.com")
            car = st.text_input("Car", placeholder="Toyota Corolla")
            submitted = st.form_submit_button("Start Chat", use_container_width=True)
        if submitted and name and car and is_valid_email(new_email):
            try:
                api_register(name, new_email, car)
                ss.user_registered = True
                ss.user_name = name
                ss.user_email = new_email
                ss.user_last_email = new_email
                ss.car = car
                try:
                    data = api_history(new_email)
                    ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
                except Exception as e:
                    st.warning(f"Could not load history: {e}")
                st.rerun()
            except requests.HTTPError as http_err:
                st.error(f"Registration failed: {http_err.response.text}")
            except Exception as e:
                st.error(f"Registration failed: {e}")

    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# =========================
# Main Single-Page UI
# =========================
st.markdown('<div class="app-shell"><div class="app-card">', unsafe_allow_html=True)

st.markdown("""
    <div class="app-header">
        <span style="font-size: 24px;">🚗</span>
        <h2>Insurance Assistant</h2>
    </div>
""", unsafe_allow_html=True)

# Existing chat (scrollable area inside the card)
st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
if ss.chat_history:
    render_history_list(ss.chat_history)
st.markdown('</div>', unsafe_allow_html=True)  # close chat scroll

# Optional quick actions (prefill input, not placeholder)
render_quick_actions()

# Chat input (single call + proper placeholder behavior)
handle_chat_input()

# Optional: settings section
with st.expander("⚙️ Settings / Session", expanded=False):
    st.write(f"**Name:** {ss.user_name or '—'}")
    st.write(f"**Email:** {ss.user_email or '—'}")
    st.write(f"**Car:** {ss.car or '—'}")
    if st.button("Log out & reset session", type="primary"):
        logout_reset()

st.markdown('</div></div>', unsafe_allow_html=True)
