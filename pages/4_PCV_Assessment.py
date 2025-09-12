import streamlit as st
import pandas as pd
from datetime import date
from utils.header_nav import header_nav
from utils.authen import require_role
from utils.pcv_utils import (
    get_pcv_data, get_active_projects, clear_pcv_cache,
    create_pcv_assessment, update_pcv_assessment, delete_pcv_assessment,
    get_recent_assessments, get_pcv_stats_by_division
)

st.set_page_config(page_title="PCV Assessment", page_icon="📊", layout="wide")

# Header Navigation
header_nav(current_page="pcv")

@require_role(allowed_roles=['admin', 'manager'])
def show_pcv_page():
    st.title("📊 Process Compliance Verification (PCV)")
    st.markdown("---")

    user_role = st.session_state.get("user_role")
    user_name = st.session_state.get("user_name")
    conn = st.connection("neon", type="sql")

    # --- Get projects for the current user ---
    owned_project_keys = []
    if user_role == 'manager':
        owned_projects_df = conn.query("SELECT project_key FROM project_info WHERE owner = :owner_email;", params={"owner_email": user_name})
        if not owned_projects_df.empty:
            owned_project_keys = owned_projects_df['project_key'].tolist()

    # Control buttons
    if st.button("🔄 Refresh Data"):
        clear_pcv_cache()
        st.rerun()

    # --- Main Data Display ---
    st.subheader("📋 Current PCV Assessments")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    projects_df = get_active_projects()
    if user_role == 'manager':
        projects_df = projects_df[projects_df['project_key'].isin(owned_project_keys)]

    project_options = ["All"] + list(projects_df['project_key'].unique()) if not projects_df.empty else ["All"]
    project_filter = col1.selectbox("Filter by Project", project_options, key="main_filter")
    division_filter = col2.selectbox("Filter by Division", ["All", "Division 1", "Division 2"], key="division_filter")
    limit = col3.number_input("Show records", min_value=10, max_value=500, value=50, step=10, key="main_limit")

    # Fetch data according to role and filters
    pcv_df = get_pcv_data(project_filter, division_filter, limit)
    if user_role == 'manager':
        pcv_df = pcv_df[pcv_df['project_key'].isin(owned_project_keys)]

    if pcv_df.empty:
        st.info("No PCV assessments found. Create your first assessment below!")
    else:
        st.dataframe(pcv_df, use_container_width=True, column_config={
            "pcv_id": st.column_config.NumberColumn("ID", width="small"),
            "project_key": st.column_config.TextColumn("Project", width="small"),
            "project_name": st.column_config.TextColumn("Project Name"),
            "division": st.column_config.TextColumn("Division", width="small"),
            "pcv_score": st.column_config.NumberColumn("PCV Score", format="%.1f%%"),
            "assessment_date": st.column_config.DateColumn("Assessment Date"),
            "updated_at": st.column_config.DatetimeColumn("Last Updated"),
        })

    st.markdown("---")

    # --- CRUD Operations ---
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Create", "✏️ Update", "🗑️ Delete", "📈 Analytics"])
    
    # Filter data for CRUD tabs based on role
    crud_projects_df = get_active_projects()
    if user_role == 'manager':
        crud_projects_df = crud_projects_df[crud_projects_df['project_key'].isin(owned_project_keys)]

    with tab1:
        st.subheader("➕ Create New PCV Assessment")
        if crud_projects_df.empty:
            st.warning("No active projects assigned to you to create an assessment for.")
        else:
            with st.form("create_pcv"):
                # Form fields...
                project_options = [f"{row['project_key']} - {row['project_name']}" for _, row in crud_projects_df.iterrows()]
                selected_project = st.selectbox("Project *", project_options)
                project_key = selected_project.split(" - ")[0] if selected_project else ""
                division = st.selectbox("Division *", ["Division 1", "Division 2"])
                pcv_score = st.number_input("PCV Score (%) *", min_value=0.0, max_value=100.0, value=80.0, step=0.1)
                assessment_date = st.date_input("Assessment Date *", value=date.today())
                
                if st.form_submit_button("Submit Assessment", type="primary"):
                    # Submission logic...
                    success, result = create_pcv_assessment(project_key, division, pcv_score, assessment_date)
                    if success:
                        st.success(f"✅ PCV Assessment created successfully! (ID: {result})")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")

    # For Update and Delete, filter the list of assessments shown
    pcv_crud_df = get_pcv_data("All", "All", 500) # Get all to filter down
    if user_role == 'manager':
        pcv_crud_df = pcv_crud_df[pcv_crud_df['project_key'].isin(owned_project_keys)]

    with tab2:
        st.subheader("✏️ Update PCV Assessment")
        if pcv_crud_df.empty:
            st.info("No existing assessments to update.")
        else:
            # Update form logic...
            update_options = [f"{row['pcv_id']}: {row['project_key']} - {row['division']} ({row['assessment_date']})" for _, row in pcv_crud_df.iterrows()]
            selected_record = st.selectbox("Select Assessment to Update", [""] + update_options)
            if selected_record:
                pcv_id = int(selected_record.split(":")[0])
                # ... (rest of the update form logic remains the same)

    with tab3:
        st.subheader("🗑️ Delete PCV Assessment")
        if pcv_crud_df.empty:
            st.info("No assessments to delete.")
        else:
            # Delete form logic...
            delete_options = [f"{row['pcv_id']}: {row['project_key']} - {row['division']} ({row['assessment_date']})" for _, row in pcv_crud_df.iterrows()]
            selected_delete = st.selectbox("Select Assessment to Delete", [""] + delete_options, key="del_select")
            if selected_delete:
                pcv_id = int(selected_delete.split(":")[0])
                # ... (rest of the delete form logic remains the same)

    with tab4:
        st.subheader("📈 Analytics & Insights")
        analytics_df = get_pcv_data("All", "All", 500)
        if user_role == 'manager':
            analytics_df = analytics_df[analytics_df['project_key'].isin(owned_project_keys)]
        
        if analytics_df.empty:
            st.info("No data available for analytics.")
        else:
            # Analytics logic remains the same, but now runs on filtered data
            st.subheader("🏢 Division Comparison")
            # ...

# --- Entry Point ---
show_pcv_page()