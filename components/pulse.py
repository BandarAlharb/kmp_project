import streamlit as st
import time
from datetime import datetime, timedelta
from database import add_pulse_update, get_pulse_updates
from utils import get_sample_departments, format_relative_time

def show_org_pulse(db_client):
    """Display organization pulse feature"""
    st.title("Organization Pulse 📢")
    
    # Tabs for viewing and adding updates
    tab1, tab2 = st.tabs(["View Updates", "Add Update"])
    
    with tab1:
        show_pulse_updates(db_client)
    
    with tab2:
        if st.session_state.user_role == "knowledge_manager":
            show_add_pulse_update(db_client)
        else:
            st.info("Only Knowledge Managers can add organization-wide updates.")

def show_pulse_updates(db_client):
    """Display organization updates/pulse"""
    # Time filter
    time_filter = st.radio(
        "Show updates from:",
        ["Last 24 Hours", "Last 5 Days", "All Updates"],
        horizontal=True,
        key="time_filter"
    )
    
    # Convert time filter to days
    if time_filter == "Last 24 Hours":
        days = 1
    elif time_filter == "Last 5 Days":
        days = 5
    else:
        days = 365  # Effectively all updates
    
    # Get updates from DB
    with st.spinner("Loading updates..."):
        updates = get_pulse_updates(db_client, days=days)
    
    # Department filter
    departments = ["All Departments"] + get_sample_departments()
    dept_filter = st.selectbox(
        "Filter by department:",
        departments,
        key="dept_filter"
    )
    
    # Apply department filter if not "All Departments"
    if dept_filter != "All Departments":
        updates = [u for u in updates if u.get("department") == dept_filter]
    
    # Display updates
    if not updates:
        st.info(f"No updates available for the selected time period{' and department' if dept_filter != 'All Departments' else ''}.")
    else:
        for update in updates:
            with st.expander(f"📢 {update.get('title', 'Untitled Update')} - {format_relative_time(update.get('timestamp', 0))}"):
                st.markdown(f"**Department:** {update.get('department', 'Organization-wide')}")
                st.markdown(f"**Posted:** {format_relative_time(update.get('timestamp', 0))}")
                st.markdown("---")
                st.markdown(update.get('content', 'No content available'))

def show_add_pulse_update(db_client):
    """Form for adding new organization pulse updates"""
    st.subheader("Add New Organization Update")
    
    # Form inputs
    update_title = st.text_input("Update Title:", key="update_title")
    
    update_content = st.text_area(
        "Update Content:",
        height=150,
        key="update_content"
    )
    
    department = st.selectbox(
        "Department:",
        ["Organization-wide"] + get_sample_departments(),
        key="update_department"
    )
    
    # Submit button
    if st.button("Post Update", key="submit_update", use_container_width=True):
        if not update_title.strip():
            st.error("Please enter an update title.")
            return
        
        if not update_content.strip():
            st.error("Please enter update content.")
            return
        
        # Save to database
        with st.spinner("Posting update..."):
            try:
                # Convert "Organization-wide" to a standard format
                dept = department if department != "Organization-wide" else "All"
                
                update_id = add_pulse_update(db_client, update_title, update_content, dept)
                
                # Success message
                st.success("Update posted successfully!")
                
                # Clear form
                st.session_state.update_title = ""
                st.session_state.update_content = ""
                
                # Switch to view tab
                st.session_state.active_tab = "View Updates"
                st.rerun()
                
            except Exception as e:
                st.error(f"Error posting update: {str(e)}")
