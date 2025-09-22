import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils.auth import require_role, login_form
from utils.getter import get_data

st.set_page_config(page_title="Sprint Capacity", page_icon="📊")
login_form()

# ============================ Header ============================
from utils.header_nav import header_nav
header_nav(current_page="sprint")
# ================================================================

@require_role(allowed_roles=['admin', 'manager', 'pm'])
def show_sprint_management():
    """
    Sprint Management page.
    - Admin/Manager: view + CRUD all sprints (except deleted projects).
    - PM: view + CRUD only sprints of projects they own (not deleted).
    """
    conn = st.connection("neon", type="sql")
    user_role = st.session_state.get("user_role")
    user_name = st.session_state.get("user_name")

    st.title("SMD Sprint Management")

    if st.button("Refresh"):
        try:
            get_data.clear()
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        st.rerun()

    # ------------------------------------------------------------
    # Fetch projects & sprints accessible to the user
    # ------------------------------------------------------------
    try:
        if user_role in ['admin', 'manager']:
            prj_df = conn.query("""
                SELECT project_key, project_name, owner, is_deleted
                FROM project_info;
            """)

            sprint_df = conn.query("""
                SELECT s.*
                FROM sprint_info s
                JOIN project_info p ON s.project_key = p.project_key
                WHERE p.is_deleted = FALSE
            """)

            dim_sprint = conn.query("""
                SELECT d.sprint_name, d.status, d.project_key
                FROM dim_sprint d
                JOIN project_info p ON d.project_key = p.project_key
                WHERE p.is_deleted = FALSE
            """)

        elif user_role == 'pm':
            prj_df = conn.query(
                """
                SELECT project_key, project_name, owner, is_deleted
                FROM project_info
                WHERE owner = :owner_name AND is_deleted = FALSE;
                """,
                params={"owner_name": user_name}
            )

            all_sprints = get_data("*", "sprint_info")
            all_dim_sprint = get_data(col="sprint_name, status, project_key", table_name="dim_sprint")

            project_keys = prj_df['project_key'].tolist() if not prj_df.empty else []
            sprint_df = all_sprints[all_sprints['project_key'].isin(project_keys)] if not all_sprints.empty else pd.DataFrame()
            dim_sprint = all_dim_sprint[all_dim_sprint['project_key'].isin(project_keys)] if not all_dim_sprint.empty else pd.DataFrame()

        else:
            st.error("Unknown role. Contact admin.")
            st.stop()

    except Exception as e:
        st.exception(e)
        st.error("Error fetching projects or sprints. Check DB and `get_data`.")
        st.stop()

    # Ensure DataFrames exist
    prj_df = prj_df if prj_df is not None else pd.DataFrame(columns=["project_key", "project_name", "owner"])
    sprint_df = sprint_df if sprint_df is not None else pd.DataFrame(columns=["sprint_name", "sprint_capacity", "project_key"])
    dim_sprint = dim_sprint if dim_sprint is not None else pd.DataFrame(columns=["sprint_name", "status", "project_key"])

    # ===================== Sprint Table ==========================
    st.subheader("Sprint list")
    st.dataframe(sprint_df, use_container_width=True, hide_index=True)

    # --- Helper ---
    def format_sprint_row(row):
        return f"{row['sprint_name']} | {row['project_key']}"

    sprint_options = [format_sprint_row(r) for _, r in sprint_df.iterrows()] if not sprint_df.empty else []

    # ===================== CRUD Actions ==========================
    page_option = st.selectbox("Choose action:", ["Add Sprint", "Edit Sprint", "Delete Sprint"])

    # -------------------- Add Sprint --------------------
    if page_option == "Add Sprint":
        st.subheader("Add Sprint")

        # Exclude sprints already in sprint_info
        if not sprint_df.empty and not dim_sprint.empty:
            existing_sprints = sprint_df[["sprint_name", "project_key"]].drop_duplicates()
            dim_sprint = dim_sprint.merge(
                existing_sprints,
                on=["sprint_name", "project_key"],
                how="left",
                indicator=True
            )
            dim_sprint = dim_sprint[dim_sprint["_merge"] == "left_only"].drop(columns="_merge")

        if dim_sprint.empty:
            st.info("No available sprints from dim_sprint for your projects.")
        else:
            with st.form("add_sprint_form"):
                sprint_selected = st.selectbox(
                    "Select Sprint",
                    options=[f"{row['sprint_name']} | {row['project_key']}" for _, row in dim_sprint.iterrows()],
                    key="add_selector"
                )
                sprint_name, project_key = [s.strip() for s in sprint_selected.split("|")]

                sprint_capacity = st.number_input("Sprint Capacity", min_value=0, step=1, value=0)

                submitted = st.form_submit_button("Save")
                if submitted:
                    try:
                        with conn.session as session:
                            session.execute(
                                text(
                                    """
                                    INSERT INTO sprint_info (sprint_name, project_key, sprint_capacity, updated_at)
                                    VALUES (:sprint_name, :project_key, :sprint_capacity, NOW())
                                    ON CONFLICT (sprint_name, project_key) DO UPDATE
                                    SET sprint_capacity = EXCLUDED.sprint_capacity,
                                        updated_at = NOW();
                                    """
                                ),
                                {
                                    "sprint_name": sprint_name,
                                    "project_key": project_key,
                                    "sprint_capacity": int(sprint_capacity),
                                }
                            )
                            session.commit()
                            get_data.clear()
                        st.success(f"Sprint '{sprint_name}' for project '{project_key}' saved.")
                        st.rerun()
                    except Exception as e:
                        st.exception(e)
                        st.error("Failed to save sprint. Check DB constraints.")

    # -------------------- Edit Sprint --------------------
    elif page_option == "Edit Sprint":
        st.subheader("Edit Sprint")

        if not sprint_options:
            st.info("No sprints available to edit.")
        else:
            sprint_choice = st.selectbox("Select sprint to edit:", sprint_options, key="edit_selector")
            sprint_name_selected, project_key_selected = [s.strip() for s in sprint_choice.split("|")]

            current_rows = sprint_df[
                (sprint_df['sprint_name'] == sprint_name_selected) &
                (sprint_df['project_key'] == project_key_selected)
            ]

            if current_rows.empty:
                st.error("Selected sprint not found or you don't have permission.")
            else:
                current = current_rows.iloc[0]
                with st.form("edit_sprint_form"):
                    st.text_input("Sprint Name", value=current["sprint_name"], disabled=True)
                    st.text_input("Project Key", value=current["project_key"], disabled=True)
                    edit_capacity = st.number_input(
                        "Sprint Capacity", min_value=0, step=1,
                        value=int(current["sprint_capacity"]) if pd.notna(current.get("sprint_capacity")) else 0
                    )
                    update_clicked = st.form_submit_button("Update Sprint")
                    if update_clicked:
                        try:
                            with conn.session as session:
                                session.execute(
                                    text(
                                        """
                                        UPDATE sprint_info
                                        SET sprint_capacity = :sprint_capacity, updated_at = NOW()
                                        WHERE sprint_name = :sprint_name AND project_key = :project_key
                                        """
                                    ),
                                    {
                                        "sprint_name": current["sprint_name"],
                                        "project_key": current["project_key"],
                                        "sprint_capacity": int(edit_capacity)
                                    }
                                )
                                session.commit()
                                get_data.clear()
                            st.success(f"Sprint '{current['sprint_name']}' updated.")
                            st.rerun()
                        except Exception as e:
                            st.exception(e)
                            st.error("Failed to update sprint.")

    # -------------------- Delete Sprint --------------------
    elif page_option == "Delete Sprint":
        st.subheader("Delete Sprint")

        if not sprint_options:
            st.info("No sprints available to delete.")
        else:
            sprint_choice = st.selectbox("Select sprint to delete:", sprint_options, key="delete_selector")
            sprint_name_selected, project_key_selected = [s.strip() for s in sprint_choice.split("|")]

            if st.button("Delete sprint"):
                try:
                    if user_role == 'pm':
                        allowed_projects = prj_df['project_key'].tolist()
                        if project_key_selected not in allowed_projects:
                            st.error("You don't have permission to delete this sprint.")
                            st.stop()

                    with conn.session as session:
                        session.execute(
                            text(
                                "DELETE FROM sprint_info WHERE sprint_name = :sprint_name AND project_key = :project_key"
                            ),
                            {"sprint_name": sprint_name_selected, "project_key": project_key_selected}
                        )
                        session.commit()
                        get_data.clear()
                    st.success(f"Deleted sprint '{sprint_name_selected}' for project '{project_key_selected}'.")
                    st.rerun()
                except Exception as e:
                    st.exception(e)
                    st.error("Failed to delete sprint.")

show_sprint_management()
