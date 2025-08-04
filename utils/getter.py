import streamlit as st


@st.cache_data
def get_data(col=str, table_name=str):
    conn = st.connection("neon", type="sql")
    return conn.query(f"SELECT {col} FROM {table_name}", ttl=1)

@st.cache_data
def get_user_data():
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
    try:
        conn = st.connection("neon", type="sql")
        query_result = conn.query("SELECT project_key FROM dim_project", ttl=1)
        if query_result.empty:
            return ["No projects available"]
        return query_result['project_key'].tolist()

    except Exception as e:
        print(f"Error loading projects: {str(e)}")

def clear_form(): 
    st.session_state["project_key"] = ""
    st.session_state["project_name"] = ""
    st.session_state["total_mm"] = 0.0
    st.session_state["description"] = ""