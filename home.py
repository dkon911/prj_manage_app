import streamlit as st
from utils.auth import login_form

st.set_page_config(
    page_title="Home",
    page_icon="🏠",
)

# Display the login form. The logic within login_form handles session state.
login_form()

# --- Main Page Content ---
# This content is only shown after a successful login.

if st.session_state.get("logged_in"):
    st.title("Welcome to the App!")
    st.write(f"You are logged in as **{st.session_state.user_email}** with role **{st.session_state.user_role}** and name **{st.session_state.user_name}**.")
    st.write("Navigate to other pages using the sidebar.")
else:
    # Optional: You can add a message on the home page for users who are not logged in.
    st.info("Please enter your credentials to log in.")