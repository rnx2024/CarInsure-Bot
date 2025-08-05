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
ss.setdefault("user_last_email", "")  # optional convenience
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
# Registration / Login (Email-first with fallback)
# =========================
st.markdown('<div class="app-shell"><div class="app-card">', unsafe_allow_html=True)
render_header()

if not ss.user_registered:
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="card" style="padding: 2rem;">', unsafe_allow_html=True)
        st.markdown("#### 🚗 Welcome to CarInsure Bot")
        st.caption("Enter your email to continue. If you're new, we'll ask for a few more details.")

        # Step 1: Email-only attempt
        with st.form("email_first_form", clear_on_submit=False):
            email = st.text_input("Email", value=ss.get("user_last_email", ""), placeholder="you@email.com")
            email_submit = st.form_submit_button("Continue", use_container_width=True)

        if email_submit:
            if not is_valid_email(email):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    data = api_history(email)  # If email exists, this should succeed
                    ss.user_email = email
                    ss.user_last_email = email
                    ss.chat_history = data.get("history", []) if isinstance(data, dict) else []
                    # We may not have name/car from history; keep them if already in session
                    ss.user_registered = True
                    st.rerun()
                except requests.HTTPError as http_err:
                    # If backend returns 404/NotFound for unknown email, fall through to full registration
                    pass
                except Exception as e:
                    st.warning(f"Could not verify email: {e}")

        # Step 2: Full registration fallback (only if not registered yet)
        if not ss.user_registered:
            st.markdown("---")
            st.caption("New here? Please register below.")
            with st.form("user_form", clear_on_submit=False):
                name = st.text_input("Name", placeholder="John Doe")
                new_email = st.text_input("Confirm Email", value=email or "", placeholder="you@email.com")
                car = st.text_input("Car", placeholder="Toyota Corolla")
                submitted = st.form_submit_button("Start Chat", use_container_width=True)

            if submitted:
                if not name or not new_email or not car:
                    st.warning("Please complete all fields.")
                elif not is_valid_email(new_email):
                    st.warning("Please enter a valid email address.")
                else:
                    try:
                        api_register(name, new_email, car)
                    except requests.HTTPError as http_err:
                        st.error(f"Registration failed: {http_err.response.text}")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")
                    else:
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

        st.markdown('</div>', unsafe_allow_html=True)

    # Close wrappers and return (avoid st.stop before closing wrappers)
    st.markdown('</div></div>', unsafe_allow_html=True)
    return  # end early after drawing login/registration card

# =========================
# Main Single-Page UI (inside same centered card)
# =========================
# Greeting only once
if ss.user_registered and not ss.greeted:
    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(f"Hi {ss.user_name or ss.user_email}, how can I help you today?")
    ss.greeted = True

# Quick actions
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("**Quick questions**")
render_quick_actions()
st.markdown('</div>', unsafe_allow_html=True)

# Existing chat (scrollable area)
st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
if ss.chat_history:
    render_history_list(ss.chat_history)
st.markdown('</div>', unsafe_allow_html=True)

# Chat input
handle_chat_input()

# Optional: simple settings section at the bottom of the card
with st.expander("⚙️ Settings / Session", expanded=False):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(f"**Name:** {ss.user_name or '—'}")
    st.write(f"**Email:** {ss.user_email or '—'}")
    st.write(f"**Car:** {ss.car or '—'}")
    st.write("")
    if st.button("Log out & reset session", type="primary"):
        logout_reset()
    st.markdown('</div>', unsafe_allow_html=True)

# Close centered wrappers
st.markdown('</div></div>', unsafe_allow_html=True)
