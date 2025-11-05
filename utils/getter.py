import streamlit as st

@st.cache_data
def get_data(col=str, table_name=str):
    conn = st.connection("neon", type="sql")
    return conn.query(f"SELECT {col} FROM {table_name}", ttl=1)

@st.cache_data
def get_user_data():
    """
    Fetch user data from the database.

    Returns:
        list: A list of user names.
    """    
    try:
        conn = st.connection("neon", type="sql")
        query_result = conn.query("SELECT user_name FROM dim_user WHERE user_name IS NOT NULL", ttl=1)
        if query_result.empty:
            return ["No users available"]
        return query_result['user_name'].tolist()
        
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        return ["Admin", "User1", "User2"]


def get_prj_data():
    """Fetch project keys that either don't have an owner or are deleted.

    Returns:
        list[str]: List of project keys with no owner or marked as deleted.
    """
    try:
        conn = st.connection("neon", type="sql")

        query = """
            SELECT project_key
            FROM dim_project
            WHERE owner IS NULL OR is_deleted = TRUE
        """

        result = conn.query(query, ttl=1)

        if result.empty:
            return []
        return result['project_key'].tolist()

    except Exception as e:
        st.error(f"Error fetching project data: {e}")
        return []


def clear_form(): 
    st.session_state["project_key"] = ""
    st.session_state["project_name"] = ""
    st.session_state["total_mm"] = 0.0
    st.session_state["description"] = ""


def clear_project_cache():
    """Clear cached data for project management and global caches."""
    try:
        get_data.clear()
    except Exception:
        pass
    try:
        get_user_data.clear()
    except Exception:
        pass
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass