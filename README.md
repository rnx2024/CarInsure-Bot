# 🚗 CarInsure Bot – AI Insurance Policy Assistant

**CarInsure Bot** is an interactive insurance assistant built with LlamaIndex, Streamlit, and GPT-4o. It provides instant answers to policyholders or inquiring customers by retrieving answers directly from uploaded insurance documents.

---

## 🔍 Features
```
- 💬 **Conversational UI** powered by GPT-4o
- 📄 **RAG-based search** using LlamaIndex over PDF, TXT, and Markdown files
- 🧠 **Memory recall** with chat history per user using SQLite
- 📁 **Offline document storage** – no uploading needed
- 🎨 **Modern UI** with custom fonts, colors, and responsive layout
- 👤 **User identification** (Name, Email, Car) before chat starts
- 📌 **Quick Questions** shortcut buttons for common inquiries
- ✅ Designed for **private deployment** (no Streamlit branding)
```
---

## 🧠 Tech Stack
```
- [Streamlit](https://streamlit.io/)
- [LlamaIndex](https://www.llamaindex.ai/)
- [OpenAI GPT-4o](https://platform.openai.com/docs/models/gpt-4o)
- [SQLite3](https://www.sqlite.org/index.html)
- [Langdetect](https://pypi.org/project/langdetect/) – detects question language
```
---

## 🚀 Usage

### 1. Clone the Repo

```
git clone https://github.com/rnx2024/LlamaIndex.git
cd LlamaIndex
```
**2. Install Requirements**
```
pip install -r requirements.txt
```
**3. Add Documents**

Place insurance policy documents (.pdf, .txt, .md) in the docs/ folder.

**4. Configure Secrets**
Create a .streamlit/secrets.toml file:

```
openai_api_key = "sk-..."
```
**5. Run the App**
```
streamlit run app.py
```

## 🧩 File Structure
```
├── app.py                 # Main Streamlit app (LlamaIndex + SQLite)
├── users.db               # SQLite DB for users and chat logs
├── docs/                  # Local folder containing reference documents
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

## ✨ Example Questions
```
1.What does this policy cover?
2.What are the exclusions?
3. How do I make a claim?
4. How long does the claim process take?
5. How do I update my policy information?
```
**Note:** Chat history is saved per user using their email, and reloaded for better context.

📄 License
MIT — free to use, modify, and share. Attribution is highly encouraged.

_**Developed by rnx2024 **_
