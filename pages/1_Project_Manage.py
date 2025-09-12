import streamlit as st
from sqlalchemy import text
from utils.authen import require_role
from utils.getter import get_data, get_user_data, get_prj_data, clear_form

st.set_page_config(page_title="Project Info", page_icon="random")

# ============================ Header ============================
from utils.header_nav import header_nav
header_nav(current_page="project")
# ================================================================

@require_role(allowed_roles=['admin', 'manager'])
def show_project_management():
    """
    Main function to display the project management page.
    Data is filtered based on the user's role.
    """
    conn = st.connection("neon", type="sql")

    st.title("SMD Project Management")
    st.write("Manage projects and their details here.")
    
    if st.button("Refresh"):
        get_data.clear()
        st.rerun()

    # --- Data Filtering based on Role ---
    user_role = st.session_state.get("user_role")
    user_name = st.session_state.get("user_name")
    
    df = None
    if user_role == 'admin':
        df = get_data("*", "project_info")
    elif user_role == 'manager':
        # Assumes the 'owner' column in 'project_info' stores the manager's email  
        df = conn.query(
            "SELECT * FROM project_info WHERE owner = :owner_email;",
            params={"owner_email": user_name}
        )

    if df is None or df.empty:
        st.warning("No projects found.")
        # Still allow admins to add projects even if none are found
        if user_role != 'admin':
            st.stop()
    
    st.dataframe(df, use_container_width=True)
    
    # --- CRUD Actions ---
    # Only admins can Add/Delete. Managers can only Edit.
    if user_role == 'admin':
        page_option = st.selectbox("Choose action:", ["Add Project", "Edit Project", "Delete Project"])
    else: # manager
        page_option = st.selectbox("Choose action:", ["Edit Project"])

    # -------------------- Add Project --------------------
    if page_option == "Add Project":
        if user_role != 'admin':
            st.error("You do not have permission to add projects.")
            st.stop()
            
        owner_list = get_user_data()
        project_key_list = get_prj_data()
        st.subheader("Add Project")

        with st.form("add_project"):
            project_key = st.selectbox("Project Key", options=project_key_list, key="add_selector")
            project_name = st.text_input("Project Name")
            total_mm = st.number_input("ManMonth (total)", min_value=0, step=1)
            project_type = st.selectbox("Project Type", ["T&M", "Fixed Price", "Other"])
            scope = st.selectbox("Workflow Type", ["Simple Workflow", "Standard Workflow", "Complicated Workflow"])
            owner = st.selectbox("PM", options=owner_list)
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            status = st.selectbox("Status", ["Active", "In-Active", "Closed"])
            submitted = st.form_submit_button("Save")

            if submitted:
                if not project_key or not project_name:
                    st.error("Project Key and Project Name are required!")
                else:
                    with conn.session as session:
                        session.execute(
                            text('''
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
                            '''),
                            {
                                "project_key": project_key, "project_name": project_name, "total_mm": total_mm,
                                "project_type": project_type, "scope": scope, "owner": owner,
                                "start_date": start_date, "end_date": end_date, "status": status
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
                    "Scope", ["Simple Workflow", "Standard Workflow", "Complicated Workflow"],
                    index=["Simple Workflow", "Standard Workflow", "Complicated Workflow"].index(current_project.get("scope", "Simple Workflow"))
                )
                # Admin can change owner, manager cannot
                can_change_owner = user_role == 'admin'
                edit_owner = st.selectbox(
                    "Owner", options=owner_list,
                    index=owner_list.index(current_project.get("owner", owner_list[0])),
                    disabled=(not can_change_owner)
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
                        with conn.session as session:
                            session.execute(
                                text('''
                                    UPDATE project_info 
                                    SET project_name = :project_name, total_mm = :total_mm,
                                        project_type = :project_type, scope = :scope, owner = :owner,
                                        start_date = :start_date, end_date = :end_date, status = :status
                                    WHERE project_key = :project_key
                                '''),
                                {
                                    "project_key": project_to_edit, "project_name": edit_project_name,
                                    "total_mm": edit_total_mm, "project_type": edit_project_type,
                                    "scope": edit_scope, "owner": edit_owner, "start_date": edit_start_date,
                                    "end_date": edit_end_date, "status": edit_status
                                }
                            )
                            session.commit()
                            get_data.clear()
                        st.success(f"Project {project_to_edit} updated successfully!")
                        st.rerun()

    # -------------------- Delete Project --------------------
    elif page_option == "Delete Project":
        if user_role != 'admin':
            st.error("You do not have permission to delete projects.")
            st.stop()

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

show_project_management()
