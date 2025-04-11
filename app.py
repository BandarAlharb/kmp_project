import streamlit as st
import os
from components.chat import show_chat_interface
from components.pulse import show_org_pulse
from components.ideas import show_ideas_interface
from components.dashboard import show_dashboard
from openai_service import initialize_openai_client
from database import initialize_db

# Set page configuration
st.set_page_config(
    page_title="KMP - Knowledge Management Platform",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
def initialize_services():
    # Initialize OpenAI client
    openai_client = initialize_openai_client()
    
    # Initialize database connection
    db_client = initialize_db()
    
    return openai_client, db_client

# Initialize session state for tracking user role and current view
if 'user_role' not in st.session_state:
    st.session_state.user_role = "employee"  # Default role
if 'current_view' not in st.session_state:
    st.session_state.current_view = "chat"  # Default view

# Main application function
def main():
    # Initialize services
    openai_client, db_client = initialize_services()
    
    # Sidebar for navigation and user role selection
    with st.sidebar:
        st.title("KMP")
        st.subheader("Knowledge Management Platform")
        
        # User role selection (simplified without authentication)
        role_options = ["Employee", "Knowledge Manager"]
        selected_role = st.selectbox(
            "Select Your Role:",
            role_options,
            index=0 if st.session_state.user_role == "employee" else 1
        )
        st.session_state.user_role = selected_role.lower().replace(" ", "_")
        
        # Navigation options based on user role
        st.subheader("Navigation")
        
        if st.session_state.user_role == "employee":
            if st.button("📝 Knowledge Sharing", use_container_width=True):
                st.session_state.current_view = "chat"
            
            if st.button("📢 Organization Pulse", use_container_width=True):
                st.session_state.current_view = "pulse"
                
            if st.button("💡 Ideas & Initiatives", use_container_width=True):
                st.session_state.current_view = "ideas"
        
        elif st.session_state.user_role == "knowledge_manager":
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.current_view = "dashboard"
                
            if st.button("📝 Knowledge Sharing", use_container_width=True):
                st.session_state.current_view = "chat"
                
            if st.button("📢 Organization Pulse", use_container_width=True):
                st.session_state.current_view = "pulse"
                
            if st.button("💡 Ideas & Initiatives", use_container_width=True):
                st.session_state.current_view = "ideas"
        
        st.divider()
        st.caption("© 2023 KMP - Knowledge Management Platform")
    
    # Main content area based on current view
    if st.session_state.current_view == "chat":
        show_chat_interface(openai_client, db_client)
    elif st.session_state.current_view == "pulse":
        show_org_pulse(db_client)
    elif st.session_state.current_view == "ideas":
        show_ideas_interface(db_client)
    elif st.session_state.current_view == "dashboard" and st.session_state.user_role == "knowledge_manager":
        show_dashboard(db_client)
    else:
        # Fallback to chat interface
        st.session_state.current_view = "chat"
        show_chat_interface(openai_client, db_client)

if __name__ == "__main__":
    main()
