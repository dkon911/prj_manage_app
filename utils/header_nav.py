import streamlit as st

def render_header_navigation(current_page=""):
    """
    Render header navigation with 4 main pages.
    
    Args:
        current_page (str): Current page identifier to disable the button
                        Options: "project", "sprint", "presales", "pcv"
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button(
            "Project Management", 
            use_container_width=True,
            disabled=(current_page == "project")
        ):
            st.switch_page("pages/1_Project_Manage.py")
    
    with col2:
        if st.button(
            "Sprint Capacity", 
            use_container_width=True,
            disabled=(current_page == "sprint")
        ):
            st.switch_page("pages/2_Sprint_Capacity.py")
    
    with col3:
        if st.button(
            "Pre-sales Import", 
            use_container_width=True,
            disabled=(current_page == "presales")
        ):
            st.switch_page("pages/3_Presales_Importer.py")
    
    with col4:
        if st.button(
            "PCV Assessment", 
            use_container_width=True,
            disabled=(current_page == "pcv")
        ):
            st.switch_page("pages/4_PCV_Assessment.py")

def header_nav(current_page=""):
    """Render header navigation with divider line."""
    render_header_navigation(current_page)
    st.markdown("---")