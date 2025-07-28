import os
import sqlite3
import streamlit as st
from typing import List, Tuple
from datetime import datetime
from langdetect import detect
from langchain.schema import HumanMessage, AIMessage
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.chat_engine import CondenseQuestionChatEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
import requests
import tempfile
import base64
from streamlit_mic_recorder import mic_recorder
import openai

# ---------- Config ----------
DOCS_DIR = "./docs"
SUPPORTED_EXTS: Tuple[str, ...] = (".txt", ".md", ".pdf")
DB_PATH = "users.db"

st.set_page_config(page_title="Insurance Assistant", page_icon="🚗")
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Rubik', sans-serif;
        color: #3399FF;
    }
    .block-container { max-width: 900px; margin: auto; padding-top: 2rem; }
    .stChatInputContainer textarea { max-width: 600px !important; margin: auto; display: block; }
    .stButton>button { background-color: #e6f2ff !important; color: #004080 !important; border-radius: 8px; }
    .stChatMessage, .stMarkdown { color: #3399FF !important; }
    .stChatMessageContent { font-family: 'Rubik', sans-serif; max-width: 800px; margin: auto; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
# 🚗🏎️ CarInsure Bot
Ask about the policy coverage, exclusions, or any clause in the documents.
""")

openai_key = st.secrets["openai_api_key"]
deepgram_key = st.secrets["deepgram_api_key"]

# ---------- SQLite Setup ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            car TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Helpers ----------
def list_local_files(folder: str, exts: Tuple[str, ...]) -> List[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts))

def save_message(email: str, role: str, message: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO conversations (user_email, role, message) VALUES (?, ?, ?)", (email, role, message))
    conn.commit()
    conn.close()

def load_history(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT role, message FROM conversations WHERE user_email = ? ORDER BY timestamp ASC", (email,))
    rows = cursor.fetchall()
    conn.close()
    return [HumanMessage(content=msg) if role == "user" else AIMessage(content=msg) for role, msg in rows]

def transcribe_with_deepgram(audio_path):
    with open(audio_path, "rb") as f:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {deepgram_key}"},
            files={"audio": f},
        )
        return response.json().get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

def speak_with_openai_tts(text: str, voice="nova", model="tts-1"):
    openai.api_key = openai_key
    speech_response = openai.audio.speech.create(model=model, voice=voice, input=text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
        tmpfile.write(speech_response.read())
        audio_path = tmpfile.name
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f"""
    <audio autoplay controls>
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)
    os.remove(audio_path)

# ---------- Session State ----------
for k in ["index", "chat_history", "user_registered", "greeted"]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k else False

# ---------- User Info Collection ----------
if not st.session_state.user_registered:
    with st.form("user_form"):
        name = st.text_input("Your Name")
        email = st.text_input("Your Email")
        car = st.text_input("Type of Car")
        submitted = st.form_submit_button("Start Chat")
    if submitted and name and email and car:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO users (name, email, car) VALUES (?, ?, ?)", (name, email, car))
        conn.commit()
        conn.close()
        st.session_state.user_registered = True
        st.session_state.user_name = name
        st.session_state.user_email = email
        st.session_state.chat_history = load_history(email)
        st.rerun()
    else:
        st.stop()

# ---------- Load Documents and Create Index ----------
files = list_local_files(DOCS_DIR, SUPPORTED_EXTS)
if not files:
    st.error(f"No documents found in '{DOCS_DIR}'.")
    st.stop()

with st.spinner("📚 Indexing documents..."):
    reader = SimpleDirectoryReader(DOCS_DIR)
    documents = reader.load_data()
    embed_model = OpenAIEmbedding(api_key=openai_key)
    llm = OpenAI(model="gpt-4o", api_key=openai_key)
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    st.session_state.index = index
    st.session_state.query_engine = index.as_query_engine(llm=llm)

# ---------- Greet User ----------
if st.session_state.user_registered and not st.session_state.greeted:
    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(f"Hi {st.session_state.user_name}, nice to meet you! What can I do for you today?")
    st.session_state.greeted = True

# ---------- Voice Mode ----------
query = None
if st.toggle("🎤 Voice Mode"):
    audio_data = mic_recorder(key="mic")
    if audio_data:
        audio_bytes = audio_data["bytes"] if isinstance(audio_data, dict) and "bytes" in audio_data else audio_data
        if isinstance(audio_bytes, bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
                tmpfile.write(audio_bytes)
                audio_path = tmpfile.name
            query = transcribe_with_deepgram(audio_path)
            os.remove(audio_path)
            st.markdown(f"**You said:** {query}")

# ---------- Chat Input ----------
if not query:
    query = st.chat_input("Ask your question about the insurance policy documents:")
    with st.container():
        st.markdown("**Quick Questions:**")
        cols = st.columns(3)
        if cols[0].button("📄 What does this policy cover?"):
            query = "What does this policy cover?"
        if cols[1].button("⚠️ What are the exclusions?"):
            query = "What are the exclusions in this policy?"
        if cols[2].button("❓ How do I make a claim?"):
            query = "How do I make a claim under this policy?"

# ---------- Chat Logic ----------
if query:
    try:
        if detect(query) != "en":
            st.warning("I can only respond in English.")
            st.stop()
    except Exception:
        st.warning("Please repeat your question.")
        st.stop()

    chat_engine = CondenseQuestionChatEngine.from_defaults(
        query_engine=st.session_state.query_engine,
        llm=llm,
        chat_mode="condense_question",
        verbose=False,
    )

    response = chat_engine.chat(query)
    answer = str(response)

    st.session_state.chat_history.append(HumanMessage(content=query))
    st.session_state.chat_history.append(AIMessage(content=answer))

    save_message(st.session_state.user_email, "user", query)
    save_message(st.session_state.user_email, "assistant", answer)

    speak_with_openai_tts(answer)

# ---------- Display Chat History ----------
for msg in st.session_state.chat_history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown(msg.content)
