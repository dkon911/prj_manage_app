import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, date

@st.cache_data(ttl=1)
def get_pcv_data(project_filter="All", limit=100):
    """Get PCV assessments with caching and filtering"""
    try:
        conn = st.connection("neon", type="sql")
        
        query = """
            SELECT 
                fm.pcv_id,
                fm.project_key,
                pi.project_name,
                ds.sprint_name,
                fm.sprint_id,
                fm.pcv_score,
                fm.assessment_date,
                fm.updated_at
            FROM fact_pcv_metrics fm
            JOIN project_info pi ON fm.project_key = pi.project_key
            LEFT JOIN dim_sprint ds ON fm.sprint_id = ds.sprint_id
            WHERE 1=1
        """
        
        params = {"limit": limit}
        if project_filter != "All":
            query += " AND fm.project_key = :project_filter"
            params["project_filter"] = project_filter
        
        query += " ORDER BY fm.assessment_date DESC, fm.updated_at DESC LIMIT :limit"
        
        return conn.query(query, params=params)
    
    except Exception as e:
        st.error(f"Error loading PCV data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1)
def get_active_projects():
    """Get active projects with sprint info"""
    try:
        conn = st.connection("neon", type="sql")
        
        query = """
            SELECT DISTINCT 
                p.project_key,
                p.project_name,
                ds.sprint_id,
                ds.sprint_name
            FROM project_info p
            LEFT JOIN dim_sprint ds ON p.project_key = ds.project_key 
                AND LOWER(ds.status) = 'active'
            WHERE p.status = 'Active'
            ORDER BY p.project_key
        """
        
        return conn.query(query)
        
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return pd.DataFrame()

def clear_pcv_cache():
    """Clear all PCV related cache data"""
    get_pcv_data.clear()
    get_active_projects.clear()
    st.cache_data.clear()

def create_pcv_assessment(project_key, sprint_id, pcv_score, assessment_date):
    """Create new PCV assessment with validation"""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check for existing assessment on same date
        existing_check_query = """
            SELECT pcv_id FROM fact_pcv_metrics 
            WHERE project_key = :project_key 
            AND (:sprint_id IS NULL OR sprint_id = :sprint_id)
            AND assessment_date = :assessment_date
        """
        
        existing = conn.query(existing_check_query, params={
            "project_key": project_key,
            "sprint_id": sprint_id,
            "assessment_date": assessment_date
        })
        
        if not existing.empty:
            return False, f"Assessment already exists for {project_key} on {assessment_date}"
        
        # Insert new assessment
        with conn.session as session:
            result = session.execute(
                text("""
                    INSERT INTO fact_pcv_metrics 
                    (project_key, sprint_id, pcv_score, assessment_date)
                    VALUES (:project_key, :sprint_id, :pcv_score, :assessment_date)
                    RETURNING pcv_id
                """),
                {
                    "project_key": project_key,
                    "sprint_id": sprint_id,
                    "pcv_score": pcv_score,
                    "assessment_date": assessment_date
                }
            )
            new_id = result.fetchone()[0]
            session.commit()
        
        # Clear cache after successful insert
        clear_pcv_cache()
        
        return True, new_id
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "foreign key" in error_msg:
            if "project_key" in error_msg:
                return False, "Invalid project reference. Project may not exist in the system."
            elif "sprint_id" in error_msg:
                return False, "Invalid sprint reference. Sprint may not exist in the system."
            else:
                return False, "Foreign key constraint violation. Please check your data."
        elif "not null" in error_msg:
            return False, "Required field cannot be empty. Please fill all mandatory fields."
        elif "check constraint" in error_msg:
            return False, "PCV score must be between 0 and 100."
        else:
            return False, f"Database Error: {str(e)}"

def update_pcv_assessment(pcv_id, pcv_score, assessment_date):
    """Update existing PCV assessment"""
    try:
        conn = st.connection("neon", type="sql")
        
        with conn.session as session:
            session.execute(
                text("""
                    UPDATE fact_pcv_metrics 
                    SET pcv_score = :pcv_score,
                        assessment_date = :assessment_date,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE pcv_id = :pcv_id
                """),
                {
                    "pcv_id": pcv_id,
                    "pcv_score": pcv_score,
                    "assessment_date": assessment_date
                }
            )
            session.commit()
        
        # Clear cache after successful update
        clear_pcv_cache()
        
        return True, "Assessment updated successfully"
        
    except Exception as e:
        return False, f"Error updating assessment: {str(e)}"

def delete_pcv_assessment(pcv_id):
    """Delete PCV assessment"""
    try:
        conn = st.connection("neon", type="sql")
        
        with conn.session as session:
            session.execute(
                text("DELETE FROM fact_pcv_metrics WHERE pcv_id = :pcv_id"),
                {"pcv_id": pcv_id}
            )
            session.commit()
        
        # Clear cache after successful delete
        clear_pcv_cache()
        
        return True, "Assessment deleted successfully"
        
    except Exception as e:
        return False, f"Error deleting assessment: {str(e)}"

def get_recent_assessments(project_key, limit=3):
    """Get recent assessments for a project"""
    try:
        conn = st.connection("neon", type="sql")
        
        query = """
            SELECT pcv_id, sprint_id, pcv_score, assessment_date 
            FROM fact_pcv_metrics 
            WHERE project_key = :pk 
            ORDER BY assessment_date DESC, pcv_id DESC 
            LIMIT :limit
        """
        
        return conn.query(query, params={"pk": project_key, "limit": limit})
        
    except Exception as e:
        st.error(f"Error loading recent assessments: {e}")
        return pd.DataFrame()
