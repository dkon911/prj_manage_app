import streamlit as st
import pandas as pd
from sqlalchemy import text

@st.cache_data(ttl=30, show_spinner=False)  # Cache for 30 seconds only
def get_pcv_data(project_filter="All", division_filter="All", limit=50):
    """Get PCV assessment data with filters."""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check if division column exists first
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_pcv_metrics' 
            AND column_name = 'division'
        """
        
        column_check = conn.query(check_column_query)
        has_division = not column_check.empty
        
        if has_division:
            query = """
                SELECT 
                    fm.pcv_id,
                    fm.project_key,
                    pi.project_name,
                    COALESCE(fm.division, 'Division 1') as division,
                    fm.pcv_score,
                    fm.assessment_date,
                    fm.updated_at
                FROM fact_pcv_metrics fm
                JOIN project_info pi ON fm.project_key = pi.project_key
                WHERE 1=1
            """
        else:
            query = """
                SELECT 
                    fm.pcv_id,
                    fm.project_key,
                    pi.project_name,
                    'Division 1' as division,
                    fm.pcv_score,
                    fm.assessment_date,
                    fm.updated_at
                FROM fact_pcv_metrics fm
                JOIN project_info pi ON fm.project_key = pi.project_key
                WHERE 1=1
            """
        
        params = {"limit": limit}
        
        if project_filter != "All":
            query += " AND fm.project_key = :project_filter"
            params["project_filter"] = project_filter
            
        if division_filter != "All" and has_division:
            query += " AND COALESCE(fm.division, 'Division 1') = :division_filter"
            params["division_filter"] = division_filter
        
        query += " ORDER BY fm.assessment_date DESC, fm.updated_at DESC LIMIT :limit"
        
        return conn.query(query, params=params)
    
    except Exception as e:
        st.error(f"Error loading PCV data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)  # Cache for 1 minute only
def get_active_projects():
    """Get active projects with their current sprints."""
    try:
        conn = st.connection("neon", type="sql")
        query = """
            SELECT DISTINCT 
                project_key,
                project_name
            FROM project_info
            WHERE status = 'Active'
            ORDER BY project_key
        """
        return conn.query(query)
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return pd.DataFrame()

def clear_pcv_cache():
    """Clear all PCV-related cached data."""
    get_pcv_data.clear()
    get_active_projects.clear()
    get_recent_assessments.clear()
    get_pcv_stats_by_division.clear()
    # Clear all Streamlit cache
    st.cache_data.clear()
    st.cache_resource.clear()

def create_pcv_assessment(project_key, division, pcv_score, assessment_date):
    """Create new PCV assessment - project-based only."""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check if division column exists
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_pcv_metrics' 
            AND column_name = 'division'
        """
        
        column_check = conn.query(check_column_query)
        has_division = not column_check.empty
        
        with conn.session as session:
            if has_division:
                # Check for existing assessment
                existing_query = """
                    SELECT pcv_id FROM fact_pcv_metrics 
                    WHERE project_key = :project_key 
                    AND COALESCE(division, 'Division 1') = :division
                    AND assessment_date = :assessment_date
                """
                
                existing = session.execute(
                    text(existing_query),
                    {
                        "project_key": project_key,
                        "division": division,
                        "assessment_date": assessment_date
                    }
                ).fetchone()
                
                if existing:
                    return False, f"Assessment already exists for {project_key} - {division} on {assessment_date}"
                
                # Insert with division
                result = session.execute(
                    text("""
                        INSERT INTO fact_pcv_metrics 
                        (project_key, division, pcv_score, assessment_date)
                        VALUES (:project_key, :division, :pcv_score, :assessment_date)
                        RETURNING pcv_id
                    """),
                    {
                        "project_key": project_key,
                        "division": division,
                        "pcv_score": pcv_score,
                        "assessment_date": assessment_date
                    }
                )
            else:
                # Fallback without division column
                existing = session.execute(
                    text("""
                        SELECT pcv_id FROM fact_pcv_metrics 
                        WHERE project_key = :project_key 
                        AND assessment_date = :assessment_date
                    """),
                    {
                        "project_key": project_key,
                        "assessment_date": assessment_date
                    }
                ).fetchone()
                
                if existing:
                    return False, f"Assessment already exists for {project_key} on {assessment_date}"
                
                result = session.execute(
                    text("""
                        INSERT INTO fact_pcv_metrics 
                        (project_key, pcv_score, assessment_date)
                        VALUES (:project_key, :pcv_score, :assessment_date)
                        RETURNING pcv_id
                    """),
                    {
                        "project_key": project_key,
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
        return False, f"Database error: {str(e)}"

def update_pcv_assessment(pcv_id, pcv_score, assessment_date, division=None):
    """Update existing PCV assessment including division."""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check if division column exists
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_pcv_metrics' 
            AND column_name = 'division'
        """
        
        column_check = conn.query(check_column_query)
        has_division = not column_check.empty
        
        with conn.session as session:
            if has_division and division is not None:
                # Update with division column
                session.execute(
                    text("""
                        UPDATE fact_pcv_metrics 
                        SET pcv_score = :pcv_score,
                            assessment_date = :assessment_date,
                            division = :division,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE pcv_id = :pcv_id
                    """),
                    {
                        "pcv_id": pcv_id,
                        "pcv_score": pcv_score,
                        "assessment_date": assessment_date,
                        "division": division
                    }
                )
                success_msg = f"Assessment updated successfully! Division: {division}"
            else:
                # Update without division column (fallback)
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
                success_msg = "Assessment updated successfully! (Note: Division not updated - column doesn't exist)"
            
            session.commit()
            
            # Clear cache after successful update
            clear_pcv_cache()
            
            return True, success_msg
            
    except Exception as e:
        return False, f"Update failed: {str(e)}"

def delete_pcv_assessment(pcv_id):
    """Delete PCV assessment."""
    try:
        conn = st.connection("neon", type="sql")
        
        with conn.session as session:
            result = session.execute(
                text("DELETE FROM fact_pcv_metrics WHERE pcv_id = :pcv_id"),
                {"pcv_id": pcv_id}
            )
            
            if result.rowcount == 0:
                return False, "Assessment not found"
            
            session.commit()
            
            # Clear cache after successful deletion
            clear_pcv_cache()
            
            return True, "Assessment deleted successfully!"
            
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=30, show_spinner=False)
def get_recent_assessments(project_key, limit=5):
    """Get recent assessments for a project."""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check if division column exists
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_pcv_metrics' 
            AND column_name = 'division'
        """
        
        column_check = conn.query(check_column_query)
        has_division = not column_check.empty
        
        if has_division:
            query = """
                SELECT pcv_id, COALESCE(division, 'Division 1') as division, pcv_score, assessment_date
                FROM fact_pcv_metrics 
                WHERE project_key = :project_key 
                ORDER BY assessment_date DESC, pcv_id DESC 
                LIMIT :limit
            """
        else:
            query = """
                SELECT pcv_id, 'Division 1' as division, pcv_score, assessment_date
                FROM fact_pcv_metrics 
                WHERE project_key = :project_key 
                ORDER BY assessment_date DESC, pcv_id DESC 
                LIMIT :limit
            """
        
        return conn.query(query, params={"project_key": project_key, "limit": limit})
    except Exception as e:
        st.error(f"Error loading recent assessments: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def get_pcv_stats_by_division():
    """Get PCV statistics grouped by division."""
    try:
        conn = st.connection("neon", type="sql")
        
        # Check if division column exists
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fact_pcv_metrics' 
            AND column_name = 'division'
        """
        
        column_check = conn.query(check_column_query)
        has_division = not column_check.empty
        
        if has_division:
            query = """
                SELECT 
                    COALESCE(division, 'Division 1') as division,
                    COUNT(*) as total_assessments,
                    ROUND(AVG(pcv_score), 2) as avg_score,
                    COUNT(DISTINCT project_key) as unique_projects,
                    MAX(assessment_date) as latest_assessment
                FROM fact_pcv_metrics
                GROUP BY COALESCE(division, 'Division 1')
                ORDER BY division
            """
        else:
            query = """
                SELECT 
                    'Division 1' as division,
                    COUNT(*) as total_assessments,
                    ROUND(AVG(pcv_score), 2) as avg_score,
                    COUNT(DISTINCT project_key) as unique_projects,
                    MAX(assessment_date) as latest_assessment
                FROM fact_pcv_metrics
            """
        
        return conn.query(query)
    except Exception as e:
        st.error(f"Error loading division stats: {e}")
        return pd.DataFrame()
