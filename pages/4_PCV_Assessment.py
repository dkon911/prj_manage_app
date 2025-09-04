import streamlit as st
import pandas as pd
from datetime import date
from utils.header_nav import header_nav
from utils.pcv_utils import (
    get_pcv_data, get_active_projects, clear_pcv_cache,
    create_pcv_assessment, update_pcv_assessment, delete_pcv_assessment,
    get_recent_assessments, get_pcv_stats_by_division
)

st.set_page_config(page_title="PCV Assessment", page_icon="📊", layout="wide")

# Header Navigation
header_nav(current_page="pcv")

if True:
    st.title("📊 Process Compliance Verification (PCV)")
    st.markdown("---")
    
    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh Data"):
            clear_pcv_cache()
            st.rerun()
    
    # Division Stats
    with st.expander("📊 Division Statistics", expanded=False):
        division_stats = get_pcv_stats_by_division()
        if not division_stats.empty:
            col1, col2 = st.columns(2)
            for idx, row in division_stats.iterrows():
                with col1 if idx % 2 == 0 else col2:
                    st.metric(
                        f"{row['division']}", 
                        f"{row['avg_score']}% avg",
                        f"{row['total_assessments']} assessments"
                    )
        else:
            st.info("No division statistics available")
    
    st.subheader("📋 Current PCV Assessments")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        projects_df = get_active_projects()
        project_options = ["All"] + list(projects_df['project_key'].unique()) if not projects_df.empty else ["All"]
        project_filter = st.selectbox("Filter by Project", project_options, key="main_filter")
    
    with col2:
        division_filter = st.selectbox(
            "Filter by Division", 
            ["All", "Division 1", "Division 2"], 
            key="division_filter"
        )
    
    with col3:
        limit = st.number_input("Show records", min_value=10, max_value=500, value=50, step=10, key="main_limit")
    
    pcv_df = get_pcv_data(project_filter, division_filter, limit)
    
    if pcv_df.empty:
        st.info("No PCV assessments found. Create your first assessment below!")
    else:
        st.dataframe(
            pcv_df,
            use_container_width=True,
            column_config={
                "pcv_id": st.column_config.NumberColumn("ID", width="small"),
                "project_key": st.column_config.TextColumn("Project", width="small"),
                "project_name": st.column_config.TextColumn("Project Name"),
                "sprint_name": st.column_config.TextColumn("Sprint"),
                "division": st.column_config.TextColumn("Division", width="small"),
                "pcv_score": st.column_config.NumberColumn("PCV Score", format="%.1f%%"),
                "assessment_date": st.column_config.DateColumn("Assessment Date"),
                "updated_at": st.column_config.DatetimeColumn("Last Updated"),
            }
        )
        
        # Quick stats
        if len(pcv_df) > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Assessments", len(pcv_df))
            with col2:
                avg_score = pcv_df['pcv_score'].mean()
                st.metric("Average Score", f"{avg_score:.1f}%")
            with col3:
                latest_date = pcv_df['assessment_date'].max()
                st.metric("Latest Assessment", latest_date.strftime("%Y-%m-%d"))
            with col4:
                unique_projects = pcv_df['project_key'].nunique()
                st.metric("Projects Assessed", unique_projects)
    
    st.markdown("---")

    # CRUD Operations
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Create", "✏️ Update", "🗑️ Delete", "📈 Analytics"])
    
    with tab1:
        st.subheader("➕ Create New PCV Assessment")

        projects_df = get_active_projects()
        
        if projects_df.empty:
            st.warning("No active projects found")
        else:
            with st.form("create_pcv"):
                col1, col2 = st.columns(2)
                
                with col1:
                    project_options = [f"{row['project_key']} - {row['project_name']}" 
                                     for _, row in projects_df.iterrows()]
                    selected_project = st.selectbox("Project *", project_options)
                    project_key = selected_project.split(" - ")[0] if selected_project else ""
                    
                    division = st.selectbox("Division *", ["Division 1", "Division 2"])
                
                with col2:
                    pcv_score = st.number_input("PCV Score (%) *", min_value=0.0, max_value=100.0, value=80.0, step=0.1)
                    assessment_date = st.date_input("Assessment Date *", value=date.today())
                
                if st.form_submit_button("Submit Assessment", type="primary"):
                    if not project_key:
                        st.error("❌ Project is required")
                    elif pcv_score < 0 or pcv_score > 100:
                        st.error("❌ PCV score must be between 0-100")
                    else:
                        success, result = create_pcv_assessment(project_key, None, division, pcv_score, assessment_date)
                        
                        if success:
                            st.success(f"✅ PCV Assessment created successfully! (ID: {result})")
                            
                            # Show summary
                            st.info(f"📊 **{project_key}** - {division} - Score: **{pcv_score}%** - Date: **{assessment_date}**")
                            
                            # Show recent assessments for context
                            recent_assessments = get_recent_assessments(project_key)
                            
                            if len(recent_assessments) > 1:
                                st.write("**Recent assessments for this project:**")
                                for _, row in recent_assessments.iterrows():
                                    st.write(f"- {row['assessment_date']}: {row['division']} - {row['pcv_score']}%")
                            
                            # Auto refresh after successful creation
                            st.rerun()
                        else:
                            if "already exists" in result:
                                st.warning(f"⚠️ {result}. Try editing the existing assessment or use a different date.")
                            else:
                                st.error(f"❌ {result}")

    with tab2:
        st.subheader("✏️ Update PCV Assessment")
        pcv_df_update = get_pcv_data("All", "All", 100)
        
        if pcv_df_update.empty:
            st.info("No existing assessments to update")
        else:
            # Select record to update
            update_options = []
            for _, row in pcv_df_update.iterrows():
                sprint_info = f" - {row['sprint_name']}" if row['sprint_name'] else ""
                update_options.append(f"{row['pcv_id']}: {row['project_key']} - {row['division']}{sprint_info} - {row['pcv_score']}% ({row['assessment_date']})")
            
            selected_record = st.selectbox("Select Assessment to Update", [""] + update_options)
            
            if selected_record:
                pcv_id = int(selected_record.split(":")[0])
                current_record = pcv_df_update[pcv_df_update['pcv_id'] == pcv_id].iloc[0]
                
                with st.form("update_pcv"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text_input("Project", value=f"{current_record['project_key']} - {current_record['project_name']}", disabled=True)
                        st.text_input("Division", value=current_record['division'], disabled=True)
                        if current_record['sprint_name']:
                            st.text_input("Sprint", value=current_record['sprint_name'], disabled=True)
                    
                    with col2:
                        new_pcv_score = st.number_input("PCV Score (%)", min_value=0.0, max_value=100.0, 
                                                      value=float(current_record['pcv_score']), step=0.5)
                        new_assessment_date = st.date_input("Assessment Date", value=current_record['assessment_date'])
                    
                    if st.form_submit_button("Update Assessment", type="primary"):
                        success, message = update_pcv_assessment(pcv_id, new_pcv_score, new_assessment_date)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

    with tab3:
        st.subheader("🗑️ Delete PCV Assessment")
        pcv_df_delete = get_pcv_data("All", "All", 100)
        
        if pcv_df_delete.empty:
            st.info("No assessments to delete")
        else:
            # Select record to delete
            delete_options = []
            for _, row in pcv_df_delete.iterrows():
                sprint_info = f" - {row['sprint_name']}" if row['sprint_name'] else ""
                delete_options.append(f"{row['pcv_id']}: {row['project_key']} - {row['division']}{sprint_info} - {row['pcv_score']}% ({row['assessment_date']})")
            
            selected_delete = st.selectbox("Select Assessment to Delete", [""] + delete_options)
            
            if selected_delete:
                pcv_id = int(selected_delete.split(":")[0])
                current_record = pcv_df_delete[pcv_df_delete['pcv_id'] == pcv_id].iloc[0]
                
                # Show record details
                st.warning("⚠️ You are about to delete:")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**Project:** {current_record['project_key']}")
                with col2:
                    st.write(f"**Division:** {current_record['division']}")
                with col3:
                    st.write(f"**Sprint:** {current_record['sprint_name'] or 'N/A'}")
                with col4:
                    st.write(f"**PCV Score:** {current_record['pcv_score']}%")
                
                # Confirmation
                if st.button("🗑️ Confirm Delete", type="secondary"):
                    success, message = delete_pcv_assessment(pcv_id)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

    with tab4:
        st.subheader("📈 Analytics & Insights")
        
        pcv_df_analytics = get_pcv_data("All", "All", 500)
        
        if pcv_df_analytics.empty:
            st.info("No data available for analytics")
        else:
            # Division comparison
            st.subheader("🏢 Division Comparison")
            division_summary = pcv_df_analytics.groupby('division').agg({
                'pcv_score': ['mean', 'count', 'std'],
                'project_key': 'nunique'
            }).round(2)
            
            col1, col2 = st.columns(2)
            for idx, division in enumerate(['Division 1', 'Division 2']):
                if division in division_summary.index:
                    data = division_summary.loc[division]
                    with col1 if idx == 0 else col2:
                        st.write(f"**{division}:**")
                        st.write(f"- Average Score: {data[('pcv_score', 'mean')]:.1f}%")
                        st.write(f"- Total Assessments: {data[('pcv_score', 'count')]}")
                        st.write(f"- Projects: {data[('project_key', 'nunique')]}")
                        st.write(f"- Std Deviation: {data[('pcv_score', 'std')]:.1f}%")
            
            st.subheader("🏆 Top Performing Projects by Division")
            for division in ['Division 1', 'Division 2']:
                division_data = pcv_df_analytics[pcv_df_analytics['division'] == division]
                if not division_data.empty:
                    project_avg = division_data.groupby('project_key')['pcv_score'].agg(['mean', 'count']).round(1)
                    project_avg = project_avg.sort_values('mean', ascending=False).head(3)
                    
                    st.write(f"**{division}:**")
                    for project, data in project_avg.iterrows():
                        st.write(f"  - **{project}**: {data['mean']}% (avg from {data['count']} assessments)")

else:
    st.warning("🔐 Please log in to access PCV Assessment features")