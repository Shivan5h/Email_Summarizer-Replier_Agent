# 📬 Email Summarizer and Replier Agent (Agentic AI System)

An automatic **agentic AI system** that reads your Gmail inbox, summarizes unread emails, and allows you to generate and send replies — all through a browser-controlled automation powered by **LangGraph**, **LangChain**, **Groq**, **Redis**, and **Streamlit**.

---

## 🚀 Features

- ✅ Navigates to Gmail in a specific Chrome profile using `browser-env`
- ✅ Automatically detects and opens unread emails
- ✅ Summarizes each unread email using Groq LLM
- ✅ Displays summaries in a user-friendly Streamlit app
- ✅ Allows user to type reply instructions
- ✅ Generates professional email replies using Groq
- ✅ Sends replies with user permission via browser automation
- ✅ Caches summaries using Redis to reduce duplicate computation

---

## 🧠 Agent Workflow

1. **Navigate to Gmail** using `browser-env` and `AutoBrowser`
2. **Traverse the inbox** top-down, stopping at the first read email
3. **Summarize all unread emails**
4. **Display summaries on Streamlit** with:
    - Sender name
    - Time received
    - Summary
    - Reply text box
5. **User types reply** → AI turns it into a professional email
6. **User confirms** → Email is sent via Gmail automatically

---

## 🛠 Tech Stack

| Tech         | Purpose                                   |
|--------------|-------------------------------------------|
| **LangGraph**   | Workflow orchestration for the agent     |
| **LangChain**   | LLM prompt management and parsing       |
| **Groq**        | Fast LLM backend for summarization/reply|
| **Redis**       | Caching email summaries                 |
| **browser-env** | Control Chrome browser for Gmail access |
| **Streamlit**   | Web UI for viewing and replying         |

---

## 📂 Project Structure

```
email-agent/
│
├── app.py                 # Main Streamlit application
├── .env                  # Secrets (Groq key, etc.) - DO NOT COMMIT
├── requirements.txt       # All required Python packages
├── README.md              # You're here
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Shivan5h/Email_Summarizer-Replier_Agent
cd Email_Summarizer-Replier_Agent
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

```env
GROQ_API_KEY=your_groq_api_key_here
```

> ⚠️ **Never share your `.env` file or commit it to GitHub!**

---

### 5. Run the App

```bash
streamlit run app.py
```

> Ensure your Chrome profile is correctly set in the script (update `CHROME_PROFILE_PATH`).

---

## 💻 Demo Walkthrough

1. App launches and connects to your Gmail through browser automation
2. All unread emails are read and summarized
3. Summaries appear in the Streamlit interface
4. You enter reply instructions in the UI
5. Groq LLM generates a reply
6. You confirm and the email is sent via browser automation

---

## 🔐 Security & Privacy

- Your Gmail login is never shared — automation runs in your own browser profile
- Email contents are processed locally and only summarized using the Groq LLM
- Redis is used for temporary caching; no persistent storage is maintained

---

## 🙋‍♂️ Author

Shivansh Shukla  
[GitHub](https://github.com/Shivan5h) • [LinkedIn](https://www.linkedin.com/in/5hivan5h/)

---
