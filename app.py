import streamlit as st
import json
import requests
import websocket
from typing import Literal, Optional
import threading
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'ws://localhost:8003/api/v1/scorecard/chat')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8003/api/v1/scorecard')

# Configure page
st.set_page_config(
    page_title="Scorecard Chat",
    page_icon="🧠",
    layout="wide"
)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'modal'
if 'job_title' not in st.session_state:
    st.session_state.job_title = ''
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = ''
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = ''
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'scorecard_state' not in st.session_state:
    st.session_state.scorecard_state = {}
if 'ws' not in st.session_state:
    st.session_state.ws = None
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False

def load_chat_history(thread_id: str):
    """Load chat history from the API"""
    try:
        headers = {}
        if st.session_state.auth_token:
            headers['Authorization'] = f"Bearer {st.session_state.auth_token}"
        
        response = requests.get(f"{API_BASE_URL}/history/{thread_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            st.session_state.messages = data.get('messages', [])
            st.session_state.scorecard_state = data.get('state', {})
            return True
        else:
            st.error(f"Failed to load chat history: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error loading chat history: {str(e)}")
        return False

def send_websocket_message(message_type: Literal["user_message", "system_message", "state_update", "error"], 
                          job_title: str, content: str, thread_id: Optional[str] = None):
    """Send message via WebSocket using websocket-client library"""
    message = {
        "type": message_type,
        "job_title": job_title,
        "content": content
    }
    if thread_id:
        message["thread_id"] = thread_id
    
    try:
        # Create WebSocket connection with authorization header
        ws_url = WEBSOCKET_URL
        
        # Try with authorization header (Method 1 worked)
        if st.session_state.auth_token:
            headers = [f"Authorization: Bearer {st.session_state.auth_token}"]
            ws = websocket.create_connection(ws_url, header=headers, timeout=30)
        else:
            ws = websocket.create_connection(ws_url, timeout=30)
        
        try:
            # Send message
            ws.send(json.dumps(message))
            
            # Wait for response with timeout
            ws.settimeout(30)  # 30 second timeout for response
            
            # Try to receive multiple messages if needed
            responses = []
            while True:
                try:
                    response = ws.recv()
                    if response:
                        parsed_response = json.loads(response)
                        responses.append(parsed_response)
                        
                        # If we get an ai_message, that's likely our main response
                        if parsed_response.get('type') == 'ai_message':
                            break
                        
                        # If we get any response with content, use it
                        if parsed_response.get('data', {}).get('content'):
                            break
                            
                except websocket.WebSocketTimeoutException:
                    # Timeout waiting for more messages, use what we have
                    break
                except Exception as recv_error:
                    # Error receiving, break and use what we have
                    break
            
            # Return the last/best response
            if responses:
                return responses[-1]  # Return the last response
            else:
                return None
                
        finally:
            # Always close the connection
            try:
                ws.close()
            except:
                pass  # Ignore errors when closing
            
    except Exception as e:
        st.error(f"WebSocket error: {str(e)}")
        return None

def modal_page():
    """Display the initial modal page"""
    st.title("🧠 Create New Scorecard")
    st.write("Let's start with some basic information.")
    
    with st.container():
        # Authorization Token Input
        auth_token = st.text_input(
            "Authorization Token (Optional)",
            placeholder="Enter Bearer token for authentication",
            help="Enter your authorization token to access protected endpoints.",
            type="password"
        )
        
        # Job Title Input
        job_title = st.text_input(
            "Job Title *",
            placeholder="e.g., Senior Software Engineer, Marketing Manager",
            help="This will be the title of your scorecard and guide the AI conversation."
        )
        
        # Thread ID Input (Optional)
        thread_id = st.text_input(
            "Thread ID (Optional)",
            placeholder="Enter thread ID to continue existing conversation",
            help="Link this scorecard to an existing conversation for better organization."
        )
        
        # Preview Section
        st.markdown("---")
        st.subheader("Preview")
        preview_col1, preview_col2 = st.columns([1, 4])
        with preview_col1:
            st.markdown("🔵")
        with preview_col2:
            st.write(f"**{job_title if job_title else 'Your Scorecard Name'}**")
            st.write(f"*{'Not assigned to a job opening' if not thread_id else f'Thread ID: {thread_id}'}*")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("Ready to create your scorecard with WhoaAI?")
        with col3:
            if st.button("Continue to WhoaAI →", type="primary", disabled=not job_title):
                if job_title:
                    st.session_state.job_title = job_title
                    st.session_state.thread_id = thread_id if thread_id else None
                    st.session_state.auth_token = auth_token if auth_token else ''
                    
                    # If thread_id is provided, load existing history
                    if thread_id:
                        if load_chat_history(thread_id):
                            st.session_state.current_page = 'chat'
                            st.rerun()
                        else:
                            st.error("Failed to load existing conversation. Please check the thread ID.")
                    else:
                        # Start new conversation
                        st.session_state.current_page = 'chat'
                        st.rerun()

def chat_page():
    """Display the chat interface"""
    # Top bar
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.current_page = 'modal'
            st.rerun()
    with col2:
        st.markdown("### 🧠 WhoaAI Assistant")
        st.markdown("*Your intelligent scorecard companion*")
    with col3:
        st.markdown(f"**{st.session_state.job_title}**")
        if st.session_state.thread_id:
            st.markdown(f"*Thread: {st.session_state.thread_id[:8]}...*")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Chat")
        
        # Display messages with different colors
        for message in st.session_state.messages:
            if message.get('role') == 'user':
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 4px solid #2196f3; color: #000000;">
                    <strong>You:</strong> {message.get('content', '')}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #f3e5f5; padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 4px solid #9c27b0; color: #000000;">
                    <strong>WhoaAI:</strong> {message.get('content', '')}
                </div>
                """, unsafe_allow_html=True)
        
        # Use form for Enter key support
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Type your response to WhoaAI... (Press Enter to send)", 
                key="user_input", 
                disabled=st.session_state.is_loading
            )
            
            col_input1, col_input2 = st.columns([4, 1])
            with col_input1:
                send_clicked = st.form_submit_button("Send", type="primary", disabled=st.session_state.is_loading or not user_input)
            
            with col_input2:
                save_draft_clicked = st.form_submit_button("Save Draft", disabled=st.session_state.is_loading)
            
            # Handle send button click or Enter key press
            if send_clicked and user_input and not st.session_state.is_loading:
                # Set loading state and store the message to send
                st.session_state.is_loading = True
                st.session_state.pending_message = user_input.strip()
                st.rerun()
            
            # Handle save draft
            if save_draft_clicked:
                st.info("Draft saved!")
        
        # Process pending message if we're in loading state
        if st.session_state.is_loading and hasattr(st.session_state, 'pending_message'):
            user_message = st.session_state.pending_message
            
            # Add user message to session state
            st.session_state.messages.append({
                'role': 'user',
                'content': user_message
            })
            
            # Send via WebSocket
            response = send_websocket_message(
                "user_message",
                st.session_state.job_title,
                user_message,
                st.session_state.thread_id
            )
            
            if response:
                # Parse the response based on the new format
                if response.get('type') == 'ai_message' and 'data' in response:
                    # New format: content is in data.content
                    content = response['data'].get('content', 'Response received')
                    
                    # Skip "connection established" messages
                    if content.lower().strip() == 'connection established':
                        # Still update session state but don't add to messages
                        if response['data'].get('thread_id'):
                            st.session_state.thread_id = response['data']['thread_id']
                        # Update scorecard sections
                        if response['data'].get('outcomes'):
                            st.session_state.scorecard_state['outcomes'] = response['data']['outcomes']
                        if response['data'].get('culture'):
                            st.session_state.scorecard_state['culture'] = response['data']['culture']
                        if response['data'].get('boss_style'):
                            st.session_state.scorecard_state['boss_style'] = response['data']['boss_style']
                        if response['data'].get('situation'):
                            st.session_state.scorecard_state['situation'] = response['data']['situation']
                        if response['data'].get('requirements'):
                            st.session_state.scorecard_state['requirements'] = response['data']['requirements']
                        if response['data'].get('competencies'):
                            st.session_state.scorecard_state['competencies'] = response['data']['competencies']
                        if response['data'].get('mission'):
                            st.session_state.scorecard_state['mission'] = response['data']['mission']
                    else:
                        # Update thread_id if provided
                        if response['data'].get('thread_id'):
                            st.session_state.thread_id = response['data']['thread_id']
                        
                        # Update scorecard sections
                        if response['data'].get('outcomes'):
                            st.session_state.scorecard_state['outcomes'] = response['data']['outcomes']
                        if response['data'].get('culture'):
                            st.session_state.scorecard_state['culture'] = response['data']['culture']
                        if response['data'].get('boss_style'):
                            st.session_state.scorecard_state['boss_style'] = response['data']['boss_style']
                        if response['data'].get('situation'):
                            st.session_state.scorecard_state['situation'] = response['data']['situation']
                        if response['data'].get('requirements'):
                            st.session_state.scorecard_state['requirements'] = response['data']['requirements']
                        if response['data'].get('competencies'):
                            st.session_state.scorecard_state['competencies'] = response['data']['competencies']
                        if response['data'].get('mission'):
                            st.session_state.scorecard_state['mission'] = response['data']['mission']
                        
                        # Add AI response to session state
                        st.session_state.messages.append({
                            'role': 'assistant',
                            'content': content
                        })
                else:
                    # Fallback to old format
                    content = response.get('content', 'Response received')
                    # Add AI response to session state
                    st.session_state.messages.append({
                        'role': 'assistant',
                        'content': content
                    })
            
            # Clear loading state and pending message
            st.session_state.is_loading = False
            if hasattr(st.session_state, 'pending_message'):
                delattr(st.session_state, 'pending_message')
            st.rerun()
        
        # Show loading indicator
        if st.session_state.is_loading:
            with st.spinner("Sending message..."):
                st.write("Please wait while we process your message...")
    
    with col2:
        st.subheader("Scorecard Preview")
        st.markdown("🧠 **Draft (1/8)**")
        
        # Display Thread ID
        if st.session_state.thread_id:
            st.markdown(f"**Thread ID:** `{st.session_state.thread_id}`")
            st.markdown("---")
        
        # Situation Section
        st.markdown("🎯 **Situation**")
        situation_data = st.session_state.scorecard_state.get('situation', {})
        if situation_data:
            for key, value in situation_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Mission Section
        st.markdown("🏢 **Mission**")
        mission_data = st.session_state.scorecard_state.get('mission', {})
        if mission_data:
            for key, value in mission_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Key Outcomes Section
        st.markdown("🎯 **Key Outcomes**")
        outcomes_data = st.session_state.scorecard_state.get('outcomes', {})
        if outcomes_data:
            for key, value in outcomes_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Competencies Section
        st.markdown("👥 **Competencies**")
        competencies_data = st.session_state.scorecard_state.get('competencies', {})
        if competencies_data:
            for key, value in competencies_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Culture & Values Section
        st.markdown("🏢 **Culture & Values**")
        culture_data = st.session_state.scorecard_state.get('culture', {})
        if culture_data:
            for key, value in culture_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Boss Style Section
        st.markdown("👥 **Boss Style**")
        boss_style_data = st.session_state.scorecard_state.get('boss_style', {})
        if boss_style_data:
            for key, value in boss_style_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        # Requirements Section
        st.markdown("📋 **Requirements**")
        requirements_data = st.session_state.scorecard_state.get('requirements', {})
        if requirements_data:
            for key, value in requirements_data.items():
                if value:
                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.markdown("*Not set yet*")
        st.markdown("---")
        
        if st.button("Complete Scorecard", type="primary"):
            st.success("Scorecard completed!")

def main():
    """Main application logic"""
    if st.session_state.current_page == 'modal':
        modal_page()
    elif st.session_state.current_page == 'chat':
        chat_page()

if __name__ == "__main__":
    main() 