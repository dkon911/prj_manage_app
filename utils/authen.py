import streamlit as st
import hashlib
from functools import wraps

conn = st.connection("neon", type="sql")


def _hash_password(password: str) -> str:
    """Hashes the password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def _validate_user(email: str, password: str) -> tuple[bool, str]:
    """
    Validates user credentials against the database.
    Returns a tuple of (is_valid, role).
    """
    password_hash = _hash_password(password)

    query = "SELECT role, username FROM app_users WHERE email = :email AND password = :password;"
    
    df = conn.query(query, params={"email": email, "password": password_hash}, ttl=0)
    
    if not df.empty:
        # User found and password matches
        return True, df["role"].iloc[0], df["username"].iloc[0]

    return False, "", ""

def login_form() -> None:
    """
    Displays the login form and handles the authentication process.
    Manages session state for login status, user email, and role.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.user_role = ""

    if not st.session_state.logged_in:
        st.title("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                is_valid, role, username = _validate_user(email, password)
                if is_valid:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_role = role
                    st.session_state.user_name = username
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
    else:
        if st.sidebar.button("Logout"):
            logout()

def logout():
    """Clears the session state to log the user out."""
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""
    st.rerun()

def require_auth(page_function):
    """
    A decorator to protect pages that require authentication.
    It checks if the user is logged in before running the page function.
    If not logged in, it stops the execution and can optionally show a message.
    """
    @wraps(page_function)
    def wrapper(*args, **kwargs):
        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            st.warning("Please log in to access this page.")
            st.stop()
        return page_function(*args, **kwargs)
    return wrapper

def require_role(allowed_roles: list):
    """
    A decorator to protect pages based on user roles.
    It checks if the user's role is in the allowed list.
    """
    def decorator(page_function):
        @wraps(page_function)
        def wrapper(*args, **kwargs):
            # First, ensure the user is logged in
            if "logged_in" not in st.session_state or not st.session_state.logged_in:
                st.warning("Please log in to access this page.")
                st.stop()
            
            # Then, check the role
            user_role = st.session_state.get("user_role")
            if user_role not in allowed_roles:
                st.error("You do not have permission to view this page.")
                st.stop()
            
            return page_function(*args, **kwargs)
        return wrapper
    return decorator