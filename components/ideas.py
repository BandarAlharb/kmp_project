import streamlit as st
import time
from database import add_idea, get_ideas, update_idea_status, support_idea
from utils import get_sample_departments, format_relative_time

def show_ideas_interface(db_client):
    """Display ideas and initiatives interface"""
    st.title("Ideas & Initiatives 💡")
    
    # Tabs for viewing and adding ideas
    tab1, tab2 = st.tabs(["Browse Ideas", "Submit New Idea"])
    
    with tab1:
        show_ideas_list(db_client)
    
    with tab2:
        show_add_idea(db_client)

def show_ideas_list(db_client):
    """Display list of ideas and initiatives"""
    # Get all ideas
    with st.spinner("Loading ideas..."):
        ideas = get_ideas(db_client)
    
    # Filters
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Status filter
        status_options = ["All Statuses", "Proposed", "In Progress", "Completed", "Rejected"]
        status_filter = st.selectbox(
            "Filter by status:",
            status_options,
            key="status_filter"
        )
    
    with col2:
        # Department filter
        departments = ["All Departments"] + get_sample_departments()
        dept_filter = st.selectbox(
            "Filter by department:",
            departments,
            key="dept_filter"
        )
    
    # Apply filters
    filtered_ideas = ideas
    
    if status_filter != "All Statuses":
        status_value = status_filter.lower().replace(" ", "_")
        filtered_ideas = [i for i in filtered_ideas if i.get("status") == status_value]
    
    if dept_filter != "All Departments":
        filtered_ideas = [i for i in filtered_ideas if i.get("department") == dept_filter]
    
    # Display ideas
    if not filtered_ideas:
        st.info("No ideas found matching your filters.")
    else:
        for idea in filtered_ideas:
            show_idea_card(db_client, idea)

def show_idea_card(db_client, idea):
    """Display an individual idea card"""
    # Status badge color
    status = idea.get("status", "proposed")
    status_colors = {
        "proposed": "secondary",
        "in_progress": "primary",
        "completed": "success",
        "rejected": "danger"
    }
    status_color = status_colors.get(status, "secondary")
    
    # Format status text
    status_text = status.replace("_", " ").title()
    
    # Create expandable card for each idea
    with st.expander(f"💡 {idea.get('title', 'Untitled Idea')} - {format_relative_time(idea.get('timestamp', 0))}"):
        # Header with status badge
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4>{idea.get('title', 'Untitled Idea')}</h4>
                <span style="padding: 3px 10px; border-radius: 10px; background-color: {'blue' if status == 'in_progress' else 'green' if status == 'completed' else 'red' if status == 'rejected' else 'gray'}; color: white; font-size: 0.8em;">
                    {status_text}
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Idea details
        st.markdown(f"**Submitted by:** {idea.get('employee_name', 'Anonymous')} from {idea.get('department', 'Unknown')} department")
        st.markdown(f"**Submitted:** {format_relative_time(idea.get('timestamp', 0))}")
        
        # Idea description
        st.markdown("### Description")
        st.markdown(idea.get('description', 'No description provided'))
        
        # Supporters
        supporters = idea.get('supporters', [])
        supporter_count = len(supporters)
        
        st.markdown(f"### Supporters ({supporter_count})")
        if supporter_count > 0:
            # Display first 5 supporters, then "and X more" if needed
            display_supporters = supporters[:5]
            more_count = supporter_count - 5
            
            supporters_text = ", ".join(display_supporters)
            if more_count > 0:
                supporters_text += f" and {more_count} more"
            
            st.markdown(supporters_text)
        else:
            st.markdown("No supporters yet. Be the first to support this idea!")
        
        # Support button
        employee_name = st.session_state.get("employee_name", "")
        
        if employee_name and employee_name not in supporters:
            if st.button("👍 Support this idea", key=f"support_{idea.get('id')}", use_container_width=True):
                if not employee_name.strip():
                    st.warning("Please enter your name in the Knowledge Sharing section before supporting.")
                else:
                    updated_supporters = support_idea(db_client, idea.get('id'), employee_name)
                    st.success(f"You have supported this idea! Total supporters: {len(updated_supporters)}")
                    st.rerun()
        
        # Status update (for knowledge managers only)
        if st.session_state.user_role == "knowledge_manager":
            st.markdown("### Update Status (Knowledge Manager Only)")
            new_status = st.selectbox(
                "Change status:",
                ["proposed", "in_progress", "completed", "rejected"],
                index=["proposed", "in_progress", "completed", "rejected"].index(status),
                format_func=lambda x: x.replace("_", " ").title(),
                key=f"status_{idea.get('id')}"
            )
            
            if new_status != status:
                if st.button("Update Status", key=f"update_{idea.get('id')}", use_container_width=True):
                    update_idea_status(db_client, idea.get('id'), new_status)
                    st.success(f"Status updated to {new_status.replace('_', ' ').title()}")
                    st.rerun()

def show_add_idea(db_client):
    """Form for adding new ideas/initiatives"""
    st.subheader("Submit a New Idea or Initiative")
    
    # Form inputs
    idea_title = st.text_input("Idea Title:", key="idea_title")
    
    idea_description = st.text_area(
        "Describe your idea or initiative in detail:",
        height=150,
        key="idea_description"
    )
    
    # Get user info from session state or prompt for it
    employee_name = st.session_state.get("employee_name", "")
    if not employee_name:
        employee_name = st.text_input("Your Name:", key="idea_employee_name")
    
    department = st.session_state.get("user_department", "")
    if not department:
        department = st.selectbox(
            "Department:", 
            options=get_sample_departments(),
            key="idea_department"
        )
    
    # Submit button
    if st.button("Submit Idea", key="submit_idea", use_container_width=True):
        if not idea_title.strip():
            st.error("Please enter an idea title.")
            return
        
        if not idea_description.strip():
            st.error("Please enter an idea description.")
            return
        
        if not employee_name.strip():
            st.error("Please enter your name.")
            return
        
        # Save to database
        with st.spinner("Submitting your idea..."):
            try:
                idea_id = add_idea(db_client, idea_title, idea_description, employee_name, department)
                
                # Support own idea automatically
                support_idea(db_client, idea_id, employee_name)
                
                # Success message
                st.success("Your idea has been submitted successfully!")
                
                # Clear form
                st.session_state.idea_title = ""
                st.session_state.idea_description = ""
                
                # Switch to browse tab
                st.rerun()
                
            except Exception as e:
                st.error(f"Error submitting idea: {str(e)}")
