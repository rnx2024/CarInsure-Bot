import os
import sqlite3
from typing import List, Tuple
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.chat_engine import CondenseQuestionChatEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from langchain.schema import HumanMessage, AIMessage
from langdetect import detect
from datetime import datetime
import requests
import tempfile
import base64
from streamlit_mic_recorder import mic_recorder

# ---------- Config ----------
DOCS_DIR = "./docs"
SUPPORTED_EXTS: Tuple[str, ...] = (".txt", ".md", ".pdf")
DB_PATH = "users.db"

st.set_page_config(page_title="Insurance Assistant", page_icon="🚗", layout="wide")
st.markdown("""<style>
    /* Your CSS here */
</style>""", unsafe_allow_html=True)

st.markdown("""# 🚗 CarInsure Bot  
Ask about the policy coverage, exclusions, or any clause in the documents.
""")

openai_key = st.secrets["openai_api_key"]

# ---------- SQLite Setup ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (...)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS conversations (...)""")
    conn.commit()
    conn.close()

init_db()

# ---------- Helpers ----------
def list_local_files(folder: str, exts: Tuple[str, ...]) -> List[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(exts)
    )

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
    history = []
    for role, msg in rows:
        if role == "user":
            history.append(HumanMessage(content=msg))
        else:
            history.append(AIMessage(content=msg))
    return history

# ---------- Session State ----------
if "index" not in st.session_state:
    st.session_state.index = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_registered" not in st.session_state:
    st.session_state.user_registered = False
if "greeted" not in st.session_state:
    st.session_state.greeted = False

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
    query_engine = index.as_query_engine(llm=llm)
    st.session_state.index = index
    st.session_state.query_engine = query_engine

# ---------- Greet User ----------
if st.session_state.user_registered and not st.session_state.greeted:
    with st.chat_message("assistant", avatar="🚗"):
        st.markdown(f"Hi {st.session_state.user_name}, nice to meet you! What can I do for you today?")
    st.session_state.greeted = True

# ---------- Voice Mode Toggle ----------
voice_mode = st.toggle("🎤 Voice Mode")

# ---------- Handle Voice Input ----------
query = None
if voice_mode:
    audio_data = mic_recorder(key="mic")
    if audio_data is not None:
        if isinstance(audio_data, dict) and "bytes" in audio_data:
            audio_bytes = audio_data["bytes"]
        elif isinstance(audio_data, bytes):
            audio_bytes = audio_data
        else:
            st.error("Unsupported audio format received.")
            st.stop()

        # Save audio data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            tmpfile.write(audio_bytes)
            audio_path = tmpfile.name

        # Transcribe using Deepgram
        query = transcribe_with_deepgram(audio_path)
        os.remove(audio_path)

        if query:
            st.markdown(f"**You said:** {query}")
        else:
            st.warning("Transcription failed or returned empty result.")

# ---------- Text Input Fallback ----------
if not query:
    query = st.chat_input("Ask your question about the insurance policy documents:")

# ---------- Query Processing ----------
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

# ---------- Display Chat History ----------
for msg in st.session_state.chat_history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown(msg.content)
