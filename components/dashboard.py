import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_knowledge_stats, get_ideas_stats
from knowledge_manager import KnowledgeManager
from utils import get_sample_departments

def show_dashboard(db_client):
    """Display knowledge manager dashboard"""
    st.title("Knowledge Manager Dashboard 📊")
    
    # Initialize knowledge manager
    km = KnowledgeManager(db_client)
    
    # Dashboard sections
    tab1, tab2, tab3 = st.tabs(["Overview", "Department Analytics", "Content Analytics"])
    
    with tab1:
        show_overview_dashboard(db_client, km)
    
    with tab2:
        show_department_analytics(db_client, km)
        
    with tab3:
        show_content_analytics(db_client, km)

def show_overview_dashboard(db_client, km):
    """Display overview section of dashboard"""
    st.subheader("Knowledge Platform Overview")
    
    # Get statistics
    with st.spinner("Loading statistics..."):
        knowledge_stats = get_knowledge_stats(db_client)
        ideas_stats = get_ideas_stats(db_client)
        
    # Key metrics in cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Knowledge Items",
            value=knowledge_stats["total"]
        )
        
    with col2:
        st.metric(
            label="New Today",
            value=knowledge_stats["today"]
        )
        
    with col3:
        st.metric(
            label="Total Ideas",
            value=ideas_stats["total"]
        )
        
    with col4:
        st.metric(
            label="Ideas in Progress",
            value=ideas_stats["by_status"]["in_progress"]
        )
    
    # Activity over time chart
    st.subheader("Activity Over Time")
    
    activity_data = km.get_activity_over_time()
    
    if activity_data["dates"]:
        # Create DataFrame
        df = pd.DataFrame({
            "Date": pd.to_datetime(activity_data["dates"]),
            "Knowledge Contributions": activity_data["knowledge"],
            "Ideas Submitted": activity_data["ideas"]
        })
        
        # Create and display chart
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=df["Date"], 
                y=df["Knowledge Contributions"],
                mode="lines+markers",
                name="Knowledge",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=8)
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=df["Date"], 
                y=df["Ideas Submitted"],
                mode="lines+markers",
                name="Ideas",
                line=dict(color="#ff7f0e", width=2),
                marker=dict(size=8)
            )
        )
        
        fig.update_layout(
            title="Knowledge Sharing Activity",
            xaxis_title="Date",
            yaxis_title="Count",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activity data available yet.")
    
    # Top contributors
    st.subheader("Top Knowledge Contributors")
    
    top_contributors = km.get_top_contributors(limit=10)
    
    if top_contributors:
        contributor_df = pd.DataFrame(top_contributors, columns=["Employee", "Contributions"])
        
        fig = px.bar(
            contributor_df, 
            x="Contributions", 
            y="Employee",
            orientation="h",
            color="Contributions",
            color_continuous_scale="Blues"
        )
        
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            height=400,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No contributor data available yet.")

def show_department_analytics(db_client, km):
    """Display department analytics section"""
    st.subheader("Department Engagement Analytics")
    
    # Get department activity data
    with st.spinner("Loading department data..."):
        dept_activity = km.get_department_activity()
        
    if not dept_activity:
        st.info("No department activity data available yet.")
        return
    
    # Create DataFrame from department activity
    data = []
    for dept, stats in dept_activity.items():
        data.append({
            "Department": dept,
            "Knowledge Contributions": stats["knowledge_count"],
            "Ideas Submitted": stats["ideas_count"],
            "Total Activity": stats["knowledge_count"] + stats["ideas_count"],
            "Last Activity": stats["last_activity"]
        })
    
    dept_df = pd.DataFrame(data)
    
    # Sort by total activity
    dept_df = dept_df.sort_values("Total Activity", ascending=False)
    
    # Display department comparison
    st.subheader("Department Comparison")
    
    # Department activity stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=dept_df["Department"],
            y=dept_df["Knowledge Contributions"],
            name="Knowledge",
            marker_color="#1f77b4"
        )
    )
    
    fig.add_trace(
        go.Bar(
            x=dept_df["Department"],
            y=dept_df["Ideas Submitted"],
            name="Ideas",
            marker_color="#ff7f0e"
        )
    )
    
    fig.update_layout(
        barmode="stack",
        title="Activity by Department",
        xaxis_title="Department",
        yaxis_title="Count",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Department data table
    st.subheader("Department Detail")
    st.dataframe(
        dept_df[["Department", "Knowledge Contributions", "Ideas Submitted", "Total Activity", "Last Activity"]],
        use_container_width=True,
        hide_index=True
    )

def show_content_analytics(db_client, km):
    """Display content analytics section"""
    st.subheader("Knowledge Content Analytics")
    
    # Get statistics
    with st.spinner("Loading statistics..."):
        knowledge_stats = get_knowledge_stats(db_client)
        ideas_stats = get_ideas_stats(db_client)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Knowledge by time period
        time_period_data = {
            "Period": ["Today", "This Week", "This Month"],
            "Count": [
                knowledge_stats["today"], 
                knowledge_stats["week"], 
                knowledge_stats["month"]
            ]
        }
        
        time_df = pd.DataFrame(time_period_data)
        
        fig = px.bar(
            time_df,
            x="Period",
            y="Count",
            title="Knowledge Contributions by Time Period",
            color="Count",
            color_continuous_scale="Blues"
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Ideas by status
        status_data = {
            "Status": ["Proposed", "In Progress", "Completed", "Rejected"],
            "Count": [
                ideas_stats["by_status"]["proposed"],
                ideas_stats["by_status"]["in_progress"],
                ideas_stats["by_status"]["completed"],
                ideas_stats["by_status"]["rejected"]
            ]
        }
        
        status_df = pd.DataFrame(status_data)
        
        fig = px.pie(
            status_df,
            values="Count",
            names="Status",
            title="Ideas by Status",
            color="Status",
            color_discrete_map={
                "Proposed": "#9da9bb",
                "In Progress": "#1f77b4",
                "Completed": "#2ca02c",
                "Rejected": "#d62728"
            }
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Popular ideas
    st.subheader("Most Popular Ideas")
    
    popular_ideas = km.get_popular_ideas(limit=5)
    
    if popular_ideas:
        for i, idea in enumerate(popular_ideas):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{i+1}. {idea.get('title', 'Untitled')}**")
            
            with col2:
                st.write(f"From: {idea.get('department', 'Unknown')}")
            
            with col3:
                supporter_count = len(idea.get('supporters', []))
                st.write(f"👍 {supporter_count} supporters")
            
            if i < len(popular_ideas) - 1:
                st.divider()
    else:
        st.info("No idea data available yet.")
