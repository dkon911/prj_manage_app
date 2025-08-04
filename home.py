import streamlit as st

# Set the page title and layout
st.set_page_config(page_title="SmartDev LLC - Project Management", layout="centered")

# Landing page header
st.title("Welcome to SmartDev LLC's Project Management App")
st.subheader("Effortlessly manage your projects with ease and efficiency!")

# Add a brief description
st.write("""
SmartDev LLC's Project Management App is designed to help you streamline your project workflows, 
collaborate with your team, and achieve your goals faster. Select an option below to get started.
""")

# Navigation buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📄 Project Management", use_container_width=True):
        st.switch_page("pages/1_Project_Manage.py")

with col2:
    if st.button("✏️ Edit Project", use_container_width=True):
        st.switch_page("pages/2_Edit_Project.py")


