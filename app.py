import os
import time
from datetime import datetime
import streamlit as st
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
import redis
from pydantic import BaseModel
from typing import List, Dict, Any, TypedDict
from browser_use import Browser
import asyncio

# Define State
class AgentState(TypedDict):
    emails: List[Dict[str, Any]]
    summaries: List[Dict[str, Any]]
    current_email: Dict[str, Any]
    reply_content: str

# Configuration
class Config:
    def __init__(self):
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
        self.GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH", "/path/to/chrome/profile")
        self.GMAIL_URL = "https://mail.google.com"
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))

# Data Models
class EmailSummary(BaseModel):
    sender: str
    subject: str
    received_time: str
    summary: str
    original_content: str

class EmailAgent:
    def __init__(self):
        self.config = Config()
        self.redis = redis.StrictRedis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=0
        )
        self.browser = Browser(
            profile_path=self.config.CHROME_PROFILE_PATH,
            headless=False
        )
        self.llm = ChatGroq(
            temperature=0.7,
            model_name=self.config.GROQ_MODEL,
            groq_api_key=self.config.GROQ_API_KEY
        )
        
        # Initialize workflow
        self.workflow = StateGraph(AgentState)
        self._build_workflow()
    
    def _build_workflow(self):
        # Define nodes
        self.workflow.add_node("navigate_gmail", self.navigate_to_gmail)
        self.workflow.add_node("fetch_emails", self.fetch_emails)
        self.workflow.add_node("process_email", self.process_email)
        self.workflow.add_node("summarize_email", self.summarize_email)
        self.workflow.add_node("generate_reply", self.generate_reply)
        
        # Define edges
        self.workflow.add_edge("navigate_gmail", "fetch_emails")
        self.workflow.add_edge("fetch_emails", "process_email")
        self.workflow.add_edge("process_email", "summarize_email")
        self.workflow.add_edge("summarize_email", END)
        
        # Conditional edge for reply generation
        self.workflow.add_conditional_edges(
            "summarize_email",
            self.should_generate_reply,
            {"generate_reply": "generate_reply", END: END}
        )
        self.workflow.add_edge("generate_reply", END)
        
        self.workflow.set_entry_point("navigate_gmail")
        self.app = self.workflow.compile()
    
    async def navigate_to_gmail(self, state: AgentState) -> AgentState:
        """Navigate to Gmail"""
        await self.browser.start()
        page = await self.browser.get_current_page()
        await page.goto(self.config.GMAIL_URL)
        await page.wait_for_selector("div[role='main']", timeout=20000)
        return add_messages(state, {"status": "navigated_to_gmail"})
    
    async def fetch_emails(self, state: AgentState) -> AgentState:
        """Fetch unread emails"""
        page = await self.browser.get_current_page()
        elements = await page.query_selector_all("tr.zA")  # Adjust selector as needed
        emails = []
        for el in elements:
            class_attr = await el.get_attribute('class')
            is_unread = 'zE' in class_attr if class_attr else False
            if not is_unread:
                break
            sender_elem = await el.query_selector('.yX.xY .yW span')
            subject_elem = await el.query_selector('.y6 span')
            received_time_elem = await el.query_selector('.xW.xY span')
            sender = await sender_elem.inner_text() if sender_elem else ''
            subject = await subject_elem.inner_text() if subject_elem else ''
            received_time = await received_time_elem.get_attribute('title') if received_time_elem else ''
            email_id = await el.get_attribute('data-legacy-message-id')
            emails.append({
                "id": email_id,
                "sender": sender,
                "subject": subject,
                "received_time": received_time,
            })
        return add_messages(state, {"emails": emails})
    
    async def process_email(self, state: AgentState) -> AgentState:
        """Process current email"""
        if not state["emails"]:
            return add_messages(state, {"status": "no_emails"})
        
        page = await self.browser.get_current_page()
        email = state["emails"][0]
        email_elem = await page.query_selector(f"tr[data-legacy-message-id='{email['id']}']")
        if email_elem:
            await email_elem.click()
            await page.wait_for_selector('div.a3s.aXjCH')
            content_elem = await page.query_selector('div.a3s.aXjCH')
            email["content"] = await content_elem.inner_text() if content_elem else ""
        
        return add_messages(state, {
            "current_email": email,
            "remaining_emails": state["emails"][1:]
        })
    
    def summarize_email(self, state: AgentState) -> AgentState:
        """Generate email summary"""
        prompt = ChatPromptTemplate.from_template("""
            Summarize this email in bullet points:
            
            From: {sender}
            Subject: {subject}
            Received: {time}
            
            Content:
            {content}
            
            Summary:""")
        
        chain = prompt | self.llm | StrOutputParser()
        
        summary = chain.invoke({
            "sender": state["current_email"]["sender"],
            "subject": state["current_email"]["subject"],
            "time": state["current_email"]["received_time"],
            "content": state["current_email"]["content"]
        })
        
        return add_messages(state, {
            "summary": summary,
            "summaries": state.get("summaries", []) + [{
                "sender": state["current_email"]["sender"],
                "subject": state["current_email"]["subject"],
                "received_time": state["current_email"]["received_time"],
                "summary": summary,
                "content": state["current_email"]["content"]
            }]
        })
    
    def should_generate_reply(self, state: AgentState) -> str:
        """Determine if we should generate a reply"""
        return "generate_reply" if state.get("needs_reply") else END
    
    def generate_reply(self, state: AgentState) -> AgentState:
        """Generate email reply"""
        prompt = ChatPromptTemplate.from_template("""
            Write a professional reply to this email:
            
            Original:
            From: {sender}
            Subject: {subject}
            Received: {time}
            
            Content:
            {content}
            
            Reply:""")
        
        chain = prompt | self.llm | StrOutputParser()
        
        reply = chain.invoke({
            "sender": state["current_email"]["sender"],
            "subject": state["current_email"]["subject"],
            "time": state["current_email"]["received_time"],
            "content": state["current_email"]["content"]
        })
        
        return add_messages(state, {"reply_content": reply})
    
    async def run(self):
        """Execute the workflow"""
        return await self.app.invoke({"emails": [], "summaries": []})

# Streamlit UI
def main():
    st.set_page_config(page_title="Email Agent", layout="wide")
    st.title("📧 Email Agent with StateGraph")
    
    if "agent" not in st.session_state:
        st.session_state.agent = EmailAgent()
    
    if st.button("Run Email Processing"):
        result = asyncio.run(st.session_state.agent.run())
        st.session_state.result = result
        
    if "result" in st.session_state:
        st.subheader("Processing Results")
        for summary in st.session_state.result["summaries"]:
            with st.expander(f"{summary['sender']}: {summary['subject']}"):
                st.markdown(f"**Received:** {summary['received_time']}")
                st.markdown("**Summary:**")
                st.markdown(summary['summary'])
                
                if 'reply_content' in st.session_state.result:
                    st.markdown("**Generated Reply:**")
                    st.markdown(st.session_state.result['reply_content'])

if __name__ == "__main__":
    main()