import streamlit as st
from sqlalchemy import text
from utils.authen import login_form, logout_button
from utils.getter import get_data, get_user_data, get_prj_data, clear_form

st.set_page_config(page_title="Project Info", page_icon="random")

# ============================ Header ============================
col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Project Management", use_container_width=True):
        st.switch_page("pages/1_Project_Manage.py")
with col2:
    if st.button("✏️ Sprint Capacity", use_container_width=True):
        st.switch_page("pages/2_Sprint_Capacity.py")
# ================================================================

# Tạm tắt đăng nhập
if 1 > 10:
    print("Login required")
    # login_form()
else:
    # st.write(f"Welcome, {st.session_state['username']}!") 
    # logout_button()
    conn = st.connection("neon", type="sql")

    st.title("SMD Project Management")
    st.write("Manage projects and their details here.")
    
    if st.button("Refresh"):
        get_data.clear()
        st.rerun()

    df = get_data("*", "project_info")
    st.dataframe(df, use_container_width=True)
    
    page_option = st.selectbox("Choose action:", ["Add Project", "Edit Project", "Delete Project"])
    
    # -------------------- Add Project --------------------
    if page_option == "Add Project":
        owner_list = get_user_data()
        project_key = get_prj_data()
        st.subheader("Add Project")

        with st.form("add_project"):
            project_key = st.selectbox("Project Key", options=project_key, key="add_selector")
            project_name = st.text_input("Project Name")
            total_mm = st.number_input("ManMonth (total)", min_value=0, step=1)
            project_type = st.selectbox("Project Type", ["T&M", "Fixed Price", "Other"])
            scope = st.selectbox("Scope", ["Simple scope", "Standard scope", "Complicated scope"])
            owner = st.selectbox("PM", options=owner_list)
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            status = st.selectbox("Status", ["Active", "In-Active", "Closed"])
            # description = st.text_area("Description")
            submitted = st.form_submit_button("Save")

            if submitted:
                if not project_key or not project_name:
                    st.error("Project Key and Project Name are required!")
                else:
                    with conn.session as session:
                        session.execute(
                            text("""
                                INSERT INTO project_info (
                                    project_key, project_name, total_mm, project_type, scope,
                                    owner, start_date, end_date, status
                                )
                                VALUES (
                                    :project_key, :project_name, :total_mm, :project_type, :scope,
                                    :owner, :start_date, :end_date, :status
                                )
                                ON CONFLICT (project_key) DO UPDATE
                                SET project_name = EXCLUDED.project_name,
                                    total_mm = EXCLUDED.total_mm,
                                    project_type = EXCLUDED.project_type,
                                    scope = EXCLUDED.scope,
                                    owner = EXCLUDED.owner,
                                    start_date = EXCLUDED.start_date,
                                    end_date = EXCLUDED.end_date,
                                    status = EXCLUDED.status
                            """),
                            {
                                "project_key": project_key,
                                "project_name": project_name,
                                "total_mm": total_mm,
                                "project_type": project_type,
                                "scope": scope,
                                "owner": owner,
                                "start_date": start_date,
                                "end_date": end_date,
                                "status": status
                            }
                        )
                        session.commit()
                        get_data.clear()
                        clear_form()
                    st.success("Project saved!")
                    st.rerun()

    # -------------------- Edit Project --------------------
    elif page_option == "Edit Project":
        st.subheader("Edit Existing Project")
        if not df.empty:
            project_to_edit = st.selectbox("Select project to edit:", df["project_key"].tolist(), key="edit_selector")
            current_project = df[df["project_key"] == project_to_edit].iloc[0]
            owner_list = get_user_data()

            with st.form("edit_project"):
                st.text_input("Project Key", value=current_project["project_key"], disabled=True)
                edit_project_name = st.text_input("Project Name", value=current_project["project_name"])
                edit_total_mm = st.number_input(
                    "ManMonth (total)", min_value=0, step=1, 
                    value=int(current_project["total_mm"]) if current_project["total_mm"] else 0
                )
                edit_project_type = st.selectbox(
                    "Project Type", ["T&M", "Fixed Price", "Other"],
                    index=["T&M", "Fixed Price", "Other"].index(current_project.get("project_type", "T&M"))
                )
                edit_scope = st.selectbox(
                    "Scope", ["Simple scope", "Standard scope", "Complicated scope"],
                    index=["Simple scope", "Standard scope", "Complicated scope"].index(current_project.get("scope", "Simple scope"))
                )
                edit_owner = st.selectbox(
                    "Owner", options=owner_list,
                    index=owner_list.index(current_project.get("owner", owner_list[0]))
                )
                edit_start_date = st.date_input("Start Date", value=current_project["start_date"])
                edit_end_date = st.date_input("End Date", value=current_project["end_date"])
                edit_status = st.selectbox(
                    "Status", ["Active", "In-Active", "Closed"],
                    index=["Active", "In-Active", "Closed"].index(current_project.get("status", "Active"))
                )

                if st.form_submit_button("Update Project"):
                    if not edit_project_name:
                        st.error("Project Name is required!")
                    else:
                        try:
                            with conn.session as session:
                                session.execute(
                                    text("""
                                        UPDATE project_info 
                                        SET project_name = :project_name,
                                            total_mm = :total_mm,
                                            project_type = :project_type,
                                            scope = :scope,
                                            owner = :owner,
                                            start_date = :start_date,
                                            end_date = :end_date,
                                            status = :status
                                        WHERE project_key = :project_key
                                    """),
                                    {
                                        "project_key": project_to_edit,
                                        "project_name": edit_project_name,
                                        "total_mm": edit_total_mm,
                                        "project_type": edit_project_type,
                                        "scope": edit_scope,
                                        "owner": edit_owner,
                                        "start_date": edit_start_date,
                                        "end_date": edit_end_date,
                                        "status": edit_status
                                    }
                                )
                                session.commit()
                                get_data.clear()
                            st.success(f"Project {project_to_edit} updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating project: {str(e)}")

    # -------------------- Delete Project --------------------
    elif page_option == "Delete Project":
        st.subheader("Delete Project")
        if not df.empty:
            project_to_delete = st.selectbox("Select project to delete:", df["project_key"].tolist())
            if st.button("Delete project"):
                with conn.session as session:
                    session.execute(
                        text("DELETE FROM project_info WHERE project_key = :project_key"),
                        {"project_key": project_to_delete}
                    )
                    session.commit()
                    get_data.clear()
                st.success(f"Deleted project: {project_to_delete}")
                st.rerun()
