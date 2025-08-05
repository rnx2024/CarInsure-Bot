import os
import requests
import streamlit as st

# =========================
# Config
# =========================
st.set_page_config(page_title="Insurance Assistant", page_icon="🚗", layout="wide")
API_BASE = os.getenv("API_BASE", "https://carinsure-bot.onrender.com").rstrip("/")

# =========================
# Global Styles
# =========================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600&display=swap');

  html, body, [class*="css"] {
      font-family: 'Rubik', sans-serif;
      background-color: #f6f9fc;
      color: #1f2937;
  }

  /* App container max-width */
  .main .block-container {
      max-width: 900px;
      padding-top: 1.2rem;
  }

  /* Header */
  .app-header {
      display: flex; align-items: center; gap: 10px;
      margin: 4px 0 10px 0;
  }
  .app-header h2 {
      margin: 0; padding: 0; font-weight: 600;
  }

  /* Card */
  .card {
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.04);
  }

  /* Buttons */
  .stButton>button {
      background-color: #e6f2ff !important;
      color: #004080 !important;
      border-radius: 8px;
      padding: 0.45rem 0.9rem;
      font-weight: 500;
      border: 1px solid #cfe3ff;
  }
  .stButton>button:hover {
      filter: brightness(0.98);
  }

  /* Quick chips */
  .chip {
      display: inline-flex; align-items: center; gap: 6px;
      background: #f1f6ff; color: #004080;
      border: 1px solid #d7e7ff;
      border-radius: 999px; padding: 6px 10px; font-size: 0.87rem;
      cursor: pointer; user-select: none; margin-right: 8px; margin-bottom: 6px;
  }
  .chip:hover { filter: brightness(0.97); }

  /* Chat content font */
  .stChatMessageContent { font-size: 0.98rem; }

  /* Inputs rounded */
  .stTextInput>div>div>input, .stTextArea textarea {
      border-radius: 8px;
  }

  /* Divider spacing tweak */
  .tight-divider { margin-top: 6px; margin-bottom: 10px; }
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
ss.setdefault("draft_msg", "")   # for st.chat_input default text

# =========================
# Helpers
# =========================
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

def render_header():
    st.markdown(
        """
        <div class="app-header">
            <span style="font-size: 24px;">🚗</span>
            <h2>Insurance Assistant</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()

def quick_chip(label: str, value: str, key: str):
    """
    Renders a quick action chip. Clicking sets st.session_state.draft_msg (prefills chat input).
    """
    col = st.columns([1])[0]
    with col:
        if st.button(label, key=key, use_container_width=False):
            ss.draft_msg = value

def render_quick_actions():
    st.markdown("**Quick questions**")
    chips = [
        ("📄 Coverage?", "What does this policy cover?"),
        ("⚠️ Exclusions?", "What are the exclusions in this policy?"),
        ("❓ Claim Process?", "How do I make a claim under this policy?")
    ]
    # Render as inline chips (buttons)
    chip_cols = st.columns([1,1,1])
    for (i, (label, text)) in enumerate(chips):
        with chip_cols[i]:
            st.markdown(f"""<div class="chip" onclick="window.parent.streamlitSendMessage({{'type':'streamlit:setComponentValue','key':'{i}'}})">{label}</div>""",
                        unsafe_allow_html=True)
            # Fallback invisible button for accessibility / no-js
            if st.button(label, key=f"chipbtn_{i}"):
                ss.draft_msg = text

    # JS-free reliable buttons:
    st.write("")  # spacing
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📄 Coverage?", key="cover_btn", help="What does this policy cover?"):
            ss.draft_msg = "What does this policy cover?"
    with c2:
        if st.button("⚠️ Exclusions?", key="exclude_btn", help="What are the exclusions?"):
            ss.draft_msg = "What are the exclusions in this policy?"
    with c3:
        if st.button("❓ Claim Process?", key="claim_btn", help="How do I make a claim?"):
            ss.draft_msg = "How do I make a claim under this policy?"

def handle_chat_input():
    """Handles chat input send + rendering of latest assistant response."""
    if not ss.user_email:
        return

    query = st.chat_input("Type your question...", key="draft_msg")  # uses session-state-backed default
    if not query:
        return

    with st.chat_message("user", avatar="👤"):
        st.markdown(query)
    ss.chat_history.append({"role": "user", "message": query})

    answer = ""
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
    """Compact, read-only history list."""
    if not history:
        st.info("No history yet.")
        return
    for msg in history:
        role = msg.get("role", "assistant")
        text = msg.get("message", "")
        avatar = "👤" if role == "user" else "🚗"
        with st.chat_message("user" if role == "user" else "assistant", avatar=avatar):
            st.markdown(text)

def logout_reset():
    ss.user_registered = False
    ss.user_name = ""
    ss.user_email = ""
    ss.car = ""
    ss.chat_history = []
    ss.greeted = False
    ss.draft_msg = ""
    st.rerun()

# =========================
# Registration Gate
# =========================
render_header()

# ----------------- Registration -----------------
if not st.session_state.user_registered:
    # Center the card using empty columns
    left, center, right = st.columns([1, 2, 1])  # Adjust 2 for form width
    with center:
        st.markdown('<div class="card" style="padding: 2rem;">', unsafe_allow_html=True)
        st.markdown("#### 🚗 Welcome to Insurance Assistant")
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

# =========================
# Navigation (requires 1.46+)
# =========================
nav = st.navigation(["Chat", "History", "Settings"], position="top")

# =========================
# Pages
# =========================
if nav == "Chat":
    # Greeting only once
    if ss.user_registered and not ss.greeted:
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown(f"Hi {ss.user_name}, nice to meet you! How can I help you today?")
        ss.greeted = True

    # Quick actions
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_quick_actions()
    st.markdown('</div>', unsafe_allow_html=True)

    # Existing history first
    if ss.chat_history:
        render_history_list(ss.chat_history)

    # Chat input and send
    handle_chat_input()

elif nav == "History":
    st.markdown("##### Conversation History")
    st.caption("Your past questions and the assistant’s answers.")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_history_list(ss.chat_history)
    st.markdown('</div>', unsafe_allow_html=True)

elif nav == "Settings":
    st.markdown("##### Profile & Session")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(f"**Name:** {ss.user_name}")
    st.write(f"**Email:** {ss.user_email}")
    st.write(f"**Car:** {ss.car}")
    st.write("")
    if st.button("Log out & reset session", type="primary"):
        logout_reset()
    st.markdown('</div>', unsafe_allow_html=True)
