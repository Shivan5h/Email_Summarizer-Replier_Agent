import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import streamlit as st
from langgraph import graph
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import WebBaseLoader
from browser_env import AutoBrowser, BrowserEnv
from browser_env.actions import Action, ActionParsingError
from browser_env.actions import ActionTypes
import redis
from pydantic import BaseModel

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
GROQ_MODEL = "mixtral-8x7b-32768"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROME_PROFILE_PATH = "C:/Users/shiva/AppData/Local/Google/Chrome/User Data/Profile 6"  # Update this path
GMAIL_URL = "https://mail.google.com"

# Redis client for caching
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Pydantic models for data validation
class EmailSummary(BaseModel):
    sender: str
    subject: str
    received_time: str
    summary: str
    original_content: str

class EmailReply(BaseModel):
    email_id: str
    reply_content: str

# Initialize Groq LLM
llm = ChatGroq(temperature=0.7, model_name=GROQ_MODEL, groq_api_key=GROQ_API_KEY)

# Prompts
SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    """You are an expert email assistant. Summarize the following email in 3-4 bullet points.
    
    From: {sender}
    Subject: {subject}
    Received: {received_time}
    
    Email Content:
    {content}
    
    Summary:
    -"""
)

REPLY_PROMPT = ChatPromptTemplate.from_template(
    """You are helping compose a professional email reply. The original email was:
    
    From: {sender}
    Subject: {subject}
    Received: {received_time}
    
    Original Content:
    {content}
    
    The user has provided these instructions for the reply:
    {reply_instructions}
    
    Please compose a professional email response that addresses all points from the original email and incorporates the user's instructions.
    
    Reply:
    """
)

# Chains
summary_chain = SUMMARY_PROMPT | llm | StrOutputParser()
reply_chain = REPLY_PROMPT | llm | StrOutputParser()

class EmailAgent:
    def __init__(self):
        self.browser = AutoBrowser(
            headless=False,
            chrome_profile_path=CHROME_PROFILE_PATH
        )
        self.env = BrowserEnv()
        self.current_email_id = None
        self.summaries: List[EmailSummary] = []
        
    def navigate_to_gmail(self) -> None:
        """Navigate to Gmail and wait for it to load"""
        self.browser.goto(GMAIL_URL)
        time.sleep(5)  # Wait for page to load
        
    def get_unread_emails(self) -> List[Dict[str, Any]]:
        """Get all unread emails from the inbox"""
        self.browser.goto(GMAIL_URL)
        time.sleep(5)
        emails = []
        email_elements = self.browser.find_elements('css selector', 'tr.zA')  # Gmail email rows
        for elem in email_elements:
            is_unread = 'zE' in elem.get_attribute('class')  # 'zE' is Gmail's unread class
            if not is_unread:
                break  # Stop at first read email
            sender = elem.find_element('css selector', '.yX.xY .yW span').text
            subject = elem.find_element('css selector', '.y6 span').text
            received_time = elem.find_element('css selector', '.xW.xY span').get_attribute('title')
            email_id = elem.get_attribute('data-legacy-message-id')
            emails.append({
                "id": email_id,
                "sender": sender,
                "subject": subject,
                "received_time": received_time,
            })
        return emails
    
    def open_email(self, email_id: str) -> str:
        """Open a specific email and return its content"""
        self.current_email_id = email_id
        email_elem = self.browser.find_element('css selector', f'tr[data-legacy-message-id="{email_id}"]')
        email_elem.click()
        time.sleep(2)
        content_elem = self.browser.find_element('css selector', 'div.a3s.aXjCH')  # Gmail email body
        return content_elem.text
    
    def summarize_email(self, email_data: Dict[str, Any]) -> EmailSummary:
        """Generate a summary of an email"""
        # Check cache first
        cache_key = f"email_summary:{email_data['id']}"
        cached_summary = redis_client.get(cache_key)
        
        if cached_summary:
            return EmailSummary.parse_raw(cached_summary)
            
        # Generate summary
        summary = summary_chain.invoke({
            "sender": email_data["sender"],
            "subject": email_data["subject"],
            "received_time": email_data["received_time"],
            "content": email_data["content"]
        })
        
        # Create summary object
        email_summary = EmailSummary(
            sender=email_data["sender"],
            subject=email_data["subject"],
            received_time=email_data["received_time"],
            summary=summary,
            original_content=email_data["content"]
        )
        
        # Cache the summary
        redis_client.set(cache_key, email_summary.json(), ex=3600)  # Cache for 1 hour
        
        return email_summary
    
    def process_unread_emails(self) -> None:
        """Process all unread emails and generate summaries"""
        self.navigate_to_gmail()
        unread_emails = self.get_unread_emails()
        
        for email in unread_emails:
            content = self.open_email(email["id"])
            email["content"] = content
            summary = self.summarize_email(email)
            self.summaries.append(summary)
            
            # Mark as read (would use browser automation in real implementation)
            self.mark_email_as_read(email["id"])
    
    def mark_email_as_read(self, email_id: str) -> None:
        """Mark an email as read"""
        # Implement with browser automation
        pass
    
    def compose_reply(self, email_id: str, reply_instructions: str) -> str:
        """Compose a reply to an email"""
        # Find the original email
        original_summary = next(
            (s for s in self.summaries if s.sender == email_id.split('_')[0]), None
        )
        
        if not original_summary:
            return "Original email not found"
            
        # Generate reply
        reply = reply_chain.invoke({
            "sender": original_summary.sender,
            "subject": original_summary.subject,
            "received_time": original_summary.received_time,
            "content": original_summary.original_content,
            "reply_instructions": reply_instructions
        })
        
        return reply
    
    def send_reply(self, email_id: str, reply_content: str) -> bool:
        """Send a reply through Gmail"""
        # Implement with browser automation:
        # 1. Open the email
        # 2. Click reply
        # 3. Fill in the content
        # 4. Click send
        
        # For prototype, just return success
        return True

# LangGraph workflow
def create_email_workflow(agent: EmailAgent):
    workflow = graph.Graph()
    
    # Define nodes
    workflow.add_node("navigate_to_gmail", agent.navigate_to_gmail)
    workflow.add_node("get_unread_emails", agent.get_unread_emails)
    workflow.add_node("process_email", lambda emails: [agent.process_single_email(e) for e in emails])
    workflow.add_node("summarize_emails", lambda: agent.summaries)
    
    # Define edges
    workflow.add_edge("navigate_to_gmail", "get_unread_emails")
    workflow.add_edge("get_unread_emails", "process_email")
    workflow.add_edge("process_email", "summarize_emails")
    
    # Set entry point
    workflow.set_entry_point("navigate_to_gmail")
    
    return workflow.compile()

# Streamlit UI
def display_streamlit_ui(agent: EmailAgent):
    st.title("Email Summarizer and Replier Agent")
    
    if not agent.summaries:
        st.warning("No unread emails found or processed yet.")
        if st.button("Process Unread Emails"):
            with st.spinner("Processing unread emails..."):
                agent.process_unread_emails()
            st.experimental_rerun()
        return
    
    st.success(f"Found {len(agent.summaries)} unread emails")
    
    for i, summary in enumerate(agent.summaries):
        st.subheader(f"From: {summary.sender} - {summary.received_time}")
        st.markdown(f"**Subject:** {summary.subject}")
        st.markdown("**Summary:**")
        st.markdown(summary.summary)
        
        # Reply section
        with st.expander("Reply to this email"):
            reply_text = st.text_area(
                "Enter your reply instructions:",
                key=f"reply_{i}",
                height=150
            )
            
            if st.button("Generate Reply", key=f"gen_reply_{i}"):
                with st.spinner("Generating reply..."):
                    reply_content = agent.compose_reply(
                        f"{summary.sender}_{i}",  # Simulated email ID
                        reply_text
                    )
                    st.session_state[f"generated_reply_{i}"] = reply_content
                
            if f"generated_reply_{i}" in st.session_state:
                st.markdown("**Generated Reply:**")
                st.markdown(st.session_state[f"generated_reply_{i}"])
                
                if st.button("Send Reply", key=f"send_reply_{i}"):
                    success = agent.send_reply(
                        f"{summary.sender}_{i}",  # Simulated email ID
                        st.session_state[f"generated_reply_{i}"]
                    )
                    if success:
                        st.success("Reply sent successfully!")
                    else:
                        st.error("Failed to send reply")

# Main execution
if __name__ == "__main__":
    # Initialize the agent
    email_agent = EmailAgent()
    
    # Create and run the workflow
    workflow = create_email_workflow(email_agent)
    workflow.invoke({})
    
    # Display the Streamlit UI
    display_streamlit_ui(email_agent)