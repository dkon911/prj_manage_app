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
    """Fetch project keys that don't have an owner.

    Returns:
        list[str]: List of project keys with no owner.
    """
    try:
        conn = st.connection("neon", type="sql")

        all_projects = conn.query("SELECT project_key FROM dim_project", ttl=1)

        owned_projects = conn.query(
            "SELECT project_key FROM project_info WHERE owner IS NOT NULL",
            ttl=1
        )

        if not owned_projects.empty:
            owned_keys = owned_projects['project_key'].tolist()
            available_projects = all_projects[~all_projects['project_key'].isin(owned_keys)]
        else:
            available_projects = all_projects

        if available_projects.empty:
            return []
        return available_projects['project_key'].tolist()

    except Exception as e:
        st.error(f"Error fetching project data: {e}")
        return []
    except Exception as e:
        print(f"Error loading projects: {str(e)}")


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