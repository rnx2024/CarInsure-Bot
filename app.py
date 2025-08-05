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
    --bg-lightblue: #eaf4ff;   /* light blue */
    --bg-beige:     #f7f1e3;   /* beige */
    --card-bg: #ffffff;
    --text: #1f2937;
    --border: #e5e7eb;
  }}

  html, body, [class*="css"] {{
      font-family: 'Rubik', sans-serif;
      background-color: {{'var(--bg-lightblue)' if THEME_BG == 'lightblue' else 'var(--bg-beige)'}};
      color: var(--text);
  }}

  .main .block-container {{
      max-width: 1200px;
      padding-top: 0.5rem !important;
      padding-bottom: 0.5rem !important;
  }}

  /* Full-page centering shell */
  .app-shell {{
      min-height: calc(100vh - 1.5rem);
      display: flex;
      align-items: center;
      justify-content: center;
  }}

  /* Compact, square-ish card */
  .app-card {{
      width: 800px;
      max-width: 92vw;
      min-height: 70vh;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 18px 50px rgba(0,0,0,0.08);
      padding: 16px 18px;
  }}

  .app-header {{ display: flex; align-items: center; gap: 10px; margin: 2px 0 10px 0; }}
  .app-header h2 {{ margin: 0; padding: 0; font-weight: 600; }}

  .card {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.04);
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

  /* Scrollable chat area to keep the card compact */
  .chat-scroll {{
      max-height: 55vh;
      overflow-y: auto;
      padding-right: 4px;
  }}

  /* Tighter divider spacing */
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
ss.setdefault("car", "")
ss.setdefault("chat_history", [])
ss.setdefault("greeted", False)
ss.setdefault("draft_msg", "")   # used as the default for st.chat_input

# =========================
# Helpers
# =========================
def render_header():
    st.markdown(
        """
        <div class="app-header">
            <span style="font-size: 24px;">🚗</span>
            <h2>Insurance Assistant</h2>
        </div>
        <hr/>
        """,
        unsafe_allow_html=True
    )
    # st.divider()  # kept visually minimal via <hr/>

def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))

def api_register(name: str, email: str, car: str):
    r = requests.post(f"{API_BASE}/register",
                      json={"name": name, "email": email, "car": car},
                      timeout=(CONNECT_TIMEOUT, CONNECT_TIMEOUT))
    r.raise_for_status()
    return r.json() if r.content else {}

def api_history(email: str):
    r = requests.get(f"{API_BASE}/history/{email}", timeout=(CONNECT_TIMEOUT, CONNECT_TIMEOUT))
    r.raise_for_status()
    return r.json() if r.content else {}

def api_ask(email: str, message: str):
    r = requests.post(f"{API_BASE}/ask",
                      json={"email": email, "message": message},
                      timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
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
    query = st.chat_input("Type your question...", key="draft_msg")  # bound to session state
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
    # re-seed minimal keys to avoid KeyError later
    ss["user_registered"] = False
    ss["chat_history"] = []
    ss["greeted"] = False
    ss["draft_msg"] = ""
    st.rerun()

# =========================
# Registration Gate
# =========================
st.markdown('<div class="app-shell"><div class="app-card">', unsafe_allow_html=True)
render_header()

if not ss.user_registered:
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="card" style="padding: 2rem;">', unsafe_allow_html=True)
        st.markdown("#### 🚗 Welcome to CarInsure Bot")
        st.caption("Enter your details to start chatting with the assistant.")

        with st.form("user_form", clear_on_submit=False):
            name = st.text_input("Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="you@email.com")
            car = st.text_input("Car", placeholder="Toyota Corolla")
            submitted = st.form_submit_button("Start Chat", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if not name or not email or not car:
            st.warning("Please complete all fields.")
            st.stop()
        if not is_valid_email(email):
            st.warning("Please enter a valid email address.")
            st.stop()
        try:
            api_register(name, email, car)
        except requests.HTTPError as http_err:
            st.error(f"Registration failed: {http_err.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Registration failed: {e}")
            st.stop()

        ss.user_registered = True
        ss.user_name = name
        ss.user_email = email
        ss.car = car

        try:
            data = api_history(email)
            ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
        except Exception as e:
            st.warning(f"Could not load history: {e}")

        st.rerun()
    else:
        st.stop()

def page_chat():
    # Greeting only once
    if ss.user_registered and not ss.greeted:
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown(f"Hi {ss.user_name}, nice to meet you! How can I help you today?")
        ss.greeted = True

    # Quick actions
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**Quick questions**")
    render_quick_actions()
    st.markdown('</div>', unsafe_allow_html=True)

    # Show existing chat (scrollable inside the card)
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    if ss.chat_history:
        render_history_list(ss.chat_history)
    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
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
    st.write(f"**Name:** {ss.user_name}")
    st.write(f"**Email:** {ss.user_email}")
    st.write(f"**Car:** {ss.car}")
    st.write("")
    if st.button("Log out & reset session", type="primary"):
        logout_reset()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Navigation (Streamlit 1.46+) with fallback
# =========================
if hasattr(st, "navigation"):
    # Use Page objects (functions, not strings)
    pages = {
        "Assistant": [
            st.Page(page_chat, title="Chat", icon="💬"),
            st.Page(page_history, title="History", icon="📑"),
        ],
        "Account": [
            st.Page(page_settings, title="Settings", icon="⚙️"),
        ],
    }
    nav = st.navigation(pages, position="top")  # position="top" needs 1.46+
    nav.run()
else:
    # Older Streamlit: fall back to tabs
    tab_chat, tab_hist, tab_set = st.tabs(["Chat", "History", "Settings"])
    with tab_chat:
        page_chat()
    with tab_hist:
        page_history()
    with tab_set:
        page_settings()

# Close centered wrappers
st.markdown('</div></div>', unsafe_allow_html=True)
