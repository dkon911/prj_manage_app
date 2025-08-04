import streamlit as st


account_dict = {
    "admin": "admin",
    "dkon": "dkon",
    "user2": "password2",}

def login_form():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username in account_dict and password == account_dict[username]:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def logout_button():
    if st.button("Logout"):
        st.session_state.pop("logged_in", None)
        st.session_state.pop("username", None)
        st.success("Logged out!")
        st.rerun()