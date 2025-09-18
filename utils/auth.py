
import streamlit as st
import hashlib
from functools import wraps
import streamlit_cookies_manager as st_cookies
from datetime import datetime, timedelta

conn = st.connection("neon", type="sql")

def _hash_password(password: str) -> str:
    """Hash password using SHA-256.

    Args:
        password (str): The password to hash.

    Returns:
        str: The hashed password.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def _validate_user(email: str, password: str) -> tuple[bool, str, str]:
    """Validate user credentials against the database.

    Args:
        email (str): The user's email.
        password (str): The user's password.

    Returns:
        tuple[bool, str, str]: A tuple containing a boolean indicating success, the user's role, and username.
    """
    password_hash = _hash_password(password)
    query = "SELECT role, username FROM app_users WHERE email = :email AND password = :password;"
    df = conn.query(query, params={"email": email, "password": password_hash}, ttl=0)
    if not df.empty:
        return True, df["role"].iloc[0], df["username"].iloc[0]
    return False, "", ""

def logout(cookies):
    """Logout: clear session and cookies.

    Args:
        cookies (_type_): The cookie manager instance.
    """
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""
    st.session_state.user_name = ""
    if 'user_info' in cookies:
        del cookies['user_info']
    st.rerun()

def login_form():
    """
    Login form, automatically logs in if cookie exists.
    Manages login state and logout.
    """
    cookies = st_cookies.CookieManager()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.user_role = ""
        st.session_state.user_name = ""
    import json
    if not st.session_state.logged_in:
        user_info_from_cookie = cookies.get('user_info')
        if user_info_from_cookie is not None:
            try:
                user_info = json.loads(user_info_from_cookie)
                st.session_state.logged_in = True
                st.session_state.user_email = user_info['email']
                st.session_state.user_role = user_info['role']
                st.session_state.user_name = user_info['name']
            except Exception:
                pass
    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome > {st.session_state.user_role} < {st.session_state.user_name}!")
        if st.sidebar.button("Logout"):
            logout(cookies)
        return True
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
                import json
                user_data_to_store = {
                    'email': email,
                    'role': role,
                    'name': username
                }
                cookies._default_expiry = datetime.now() + timedelta(days=7)
                cookies['user_info'] = json.dumps(user_data_to_store)
                cookies.save()
                st.rerun()
            else:
                st.error("Invalid email or password.")
    return False

def require_auth(page_function):
    """
    Decorator: only allows access if logged in.
    """
    @wraps(page_function)
    def wrapper(*args, **kwargs):
        if not st.session_state.get("logged_in", False):
            st.warning("Please log in to access this page.")
            st.stop()
        return page_function(*args, **kwargs)
    return wrapper

def require_role(allowed_roles: list):
    """Decorator: only allows access if user role is in allowed_roles.

    Args:
        allowed_roles (list): List of allowed user roles.
    """
    def decorator(page_function):
        @wraps(page_function)
        def wrapper(*args, **kwargs):
            if not st.session_state.get("logged_in", False):
                st.warning("Please log in to access this page.")
                st.stop()
            user_role = st.session_state.get("user_role")
            if user_role not in allowed_roles:
                st.error("You do not have permission to access this page.")
                st.stop()
            return page_function(*args, **kwargs)
        return wrapper
    return decorator