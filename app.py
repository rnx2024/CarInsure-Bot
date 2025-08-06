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

# Theme (choose: "lightblue" or "beige")
THEME_BG = "lightblue"

# =========================
# Global Styles
# =========================
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600&display=swap');

  :root {{
    --bg-lightblue: #eaf4ff;
    --bg-beige:     #f7f1e3;
    --card-bg: #ffffff;
    --text: #1f2937;
    --border: #e5e7eb;
  }}

  html, body, [class*="css"] {{
      font-family: 'Rubik', sans-serif;
      background-color: {{'var(--bg-lightblue)' if THEME_BG == 'lightblue' else 'var(--bg-beige)'}};
      color: var(--text);
  }}

  /* Remove default top/bottom padding so content sits near the top */
  .main .block-container {{
      max-width: 1200px;
      padding-top: 0rem !important;
      padding-bottom: 0rem !important;
  }}

  /* Keep only horizontal centering; no vertical centering */
  .app-shell {{
      display: flex;
      justify-content: center;
      margin-top: 0.5rem;   /* tweak as you like */
  }}

  .stButton>button {{
      background-color: #e6f2ff !important;
      color: #004080 !important;
      border-radius: 8px;
      padding: 0.45rem 0.9rem;
      font-weight: 500;
      border: 1px solid #cfe3ff;
  }}
  .stButton>button:hover {{ filter: brightness(0.98); }}

  .stChatMessageContent {{ font-size: 0.98rem; }}
  .stTextInput>div>div>input, .stTextArea textarea {{ border-radius: 8px; }}

  .chat-scroll {{
      max-height: 55vh;
      overflow-y: auto;
      padding-right: 4px;
  }}

  hr {{ margin: 8px 0 !important; }}
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
ss.setdefault("draft_msg", "")   # used as the default for st.chat_input

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

def render_quick_actions():
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📄 Coverage?", help="What does this policy cover?"):
            ss.draft_msg = "What does this policy cover?"
    with c2:
        if st.button("⚠️ Exclusions?", help="What are the exclusions?"):
            ss.draft_msg = "What are the exclusions in this policy?"
    with c3:
        if st.button("❓ Claim Process?", help="How do I make a claim?"):
            ss.draft_msg = "How do I make a claim under this policy?"

def handle_chat_input():
    if not ss.user_email:
        return
    query = st.chat_input("Type your question...", key="draft_msg")
    if not query:
        return

    with st.chat_message("user", avatar="👤"):
        st.markdown(query)
    ss.chat_history.append({"role": "user", "message": query})

    try:
        resp = api_ask(ss.user_email, query)
        answer = (resp.get("answer") or "").strip()
    except requests.HTTPError as http_err:
        answer = f"Server error: {http_err.response.text}"
    except Exception as e:
        answer = f"Error contacting server: {e}"

    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(answer if answer else "_No answer returned_")
    ss.chat_history.append({"role": "assistant", "message": answer})

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

# =========================
# Registration / Login Gate (two options)
# =========================

# =========================
# Registration / Login Gate (render both tabs first; handle actions after)
# =========================
if not ss.user_registered:
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown("#### 🚗 Welcome to CarInsure Bot")
        st.caption("Choose an option to continue.")

        # Prepare variables so we can process after both tabs render
        submit_reg = False
        submit_login = False
        # Defaults to avoid UnboundLocalError
        name = ""
        email_reg = ""
        car = ""
        email_login = ""

        tab_new, tab_return = st.tabs(["I’m new (Register)", "I’ve used this before (Email Login)"])

        # --- New user: one-time registration ---
        with tab_new:
            with st.form("form_register", clear_on_submit=False):
                name = st.text_input("Name", placeholder="John Doe")
                email_reg = st.text_input(
                    "Email",
                    value=(ss.get("user_last_email", "") or ""),
                    placeholder="you@email.com"
                )
                car = st.text_input("Car", placeholder="Toyota Corolla")
                submit_reg = st.form_submit_button("Create account & start chatting", use_container_width=True)

        # --- Returning user: email-only login ---
        with tab_return:
            with st.form("form_login", clear_on_submit=False):
                email_login = st.text_input(
                    "Email",
                    value=ss.get("user_last_email", ""),
                    placeholder="you@email.com"
                )
                submit_login = st.form_submit_button("Continue", use_container_width=True)

        # ---- Handle actions AFTER both tabs are rendered ----
        # Registration flow
        if submit_reg:
            email_norm = (email_reg or "").strip().lower()
            if not name or not email_norm or not car:
                st.warning("Please complete all fields.")
            elif not is_valid_email(email_norm):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    # Backend returns 409 if email already exists
                    api_register(name.strip(), email_norm, car.strip())
                except requests.HTTPError as http_err:
                    status = getattr(http_err.response, "status_code", None)
                    if status == 409:
                        st.error("This email is already registered. Please use the “I’ve used this before (Email Login)” tab.")
                    else:
                        detail = http_err.response.text if getattr(http_err, "response", None) else str(http_err)
                        st.error(f"Registration failed: {detail}")
                except Exception as e:
                    st.error(f"Registration failed: {e}")
                else:
                    # Success
                    ss.user_registered = True
                    ss.user_name = name.strip()
                    ss.user_email = email_norm
                    ss.user_last_email = email_norm
                    ss.car = car.strip()
                    try:
                        data = api_history(email_norm)  # 200 even if no chats
                        ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
                    except Exception as e:
                        st.warning(f"Could not load history: {e}")
                    st.rerun()

        # Login flow
        if submit_login:
            email_login_norm = (email_login or "").strip().lower()
            if not is_valid_email(email_login_norm):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    # Backend must return 404 if user not found
                    data = api_history(email_login_norm)
                    ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
                except requests.HTTPError as http_err:
                    code = getattr(http_err.response, "status_code", None)
                    if code == 404:
                        st.error("Email not found. Please register under the 'I’m new' tab.")
                    else:
                        st.error(f"Login failed: {http_err.response.text}")
                except Exception as e:
                    st.error(f"Error verifying email: {e}")
                else:
                    ss.user_registered = True
                    ss.user_email = email_login_norm
                    ss.user_last_email = email_login_norm
                    st.rerun()

    # Final guard: user not registered yet -> stop before main UI
    st.stop()


# =========================
# Main Single-Page UI
# =========================
def page_chat():
    if ss.user_registered and not ss.greeted:
        with st.chat_message("assistant", avatar="🚗"):
            greeting_name = ss.user_name or "there"
            st.markdown(f"Hi {greeting_name}, how can I help you today?")
        ss.greeted = True

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**Quick questions**")
    render_quick_actions()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    if ss.chat_history:
        render_history_list(ss.chat_history)
    st.markdown('</div>', unsafe_allow_html=True)

    handle_chat_input()

def page_history():
    st.markdown("##### Conversation History")
    st.caption("Your past questions and the assistant’s answers.")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_history_list(ss.chat_history)
    st.markdown('</div>', unsafe_allow_html=True)

def page_settings():
    st.markdown("##### Profile & Session")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(f"**Name:** {ss.user_name or '—'}")
    st.write(f"**Email:** {ss.user_email or '—'}")
    st.write(f"**Car:** {ss.car or '—'}")
    st.write("")
    if st.button("Log out & reset session", type="primary"):
        logout_reset()
    st.markdown('</div>', unsafe_allow_html=True)


# Navigation (Streamlit 1.46+) with fallback
if hasattr(st, "navigation"):
    pages = {
        "Assistant": [
            st.Page(page_chat, title="Chat", icon="💬"),
            st.Page(page_history, title="History", icon="📑"),
        ],
        "Account": [
            st.Page(page_settings, title="Settings", icon="⚙️"),
        ],
    }
    nav = st.navigation(pages, position="top")
    nav.run()
else:
    tab_chat, tab_hist, tab_set = st.tabs(["Chat", "History", "Settings"])
    with tab_chat:
        page_chat()
    with tab_hist:
        page_history()
    with tab_set:
        page_settings()

st.markdown('</div></div>', unsafe_allow_html=True)
