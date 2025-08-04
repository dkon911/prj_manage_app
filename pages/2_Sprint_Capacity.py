import datetime
import streamlit as st
from sqlalchemy import text
from utils.authen import login_form, logout_button
from utils.getter import get_data, get_user_data, clear_form

st.set_page_config(page_title="Sprint Capacity", page_icon="random")

# Fetch data
df = get_data("*", "sprint_info")
dim_sprint = get_data(col="sprint_name, status, project_key", table_name="dim_sprint")

# ============================ Header ============================
col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Project Management", use_container_width=True):
        st.switch_page("pages/1_Project_Manage.py")
with col2:
    if st.button("✏️ Sprint Capacity", use_container_width=True):
        st.switch_page("pages/2_Sprint_Capacity.py")
# ================================================================

if 1 > 10:
    print("Login required")
    # login_form()
else:
    conn = st.connection("neon", type="sql")

    st.title("SMD Sprint Management")

    if st.button("Refresh"):
        get_data.clear()
        df = get_data("*", "sprint_info")
        st.rerun()

    st.dataframe(df, use_container_width=True)

    page_option = st.selectbox("Choose action:", ["Add Sprint", "Edit Sprint", "Delete Sprint"])

    # -------------------- Add Sprint --------------------
    if page_option == "Add Sprint":
        st.subheader("Add Sprint")
        with st.form("add_sprint"):
            sprint_selected = st.selectbox("Select sprint from dim_sprint:", dim_sprint["sprint_name"].tolist(), key="add_selector")
            sprint_capacity = st.number_input("Sprint Capacity", min_value=0, step=1)
            submitted = st.form_submit_button("Save")

            if submitted:
                with conn.session as session:
                    session.execute(
                        text("""
                            INSERT INTO sprint_info (sprint_name, sprint_capacity)
                            VALUES (:sprint_name, :sprint_capacity)
                            ON CONFLICT (sprint_name) DO UPDATE
                            SET sprint_capacity = EXCLUDED.sprint_capacity;
                        """),
                        {
                            "sprint_name": sprint_selected,
                            "sprint_capacity": sprint_capacity,
                        }
                    )
                    session.commit()
                    get_data.clear()
                st.success("Sprint saved!")
                st.rerun()

    # -------------------- Edit Sprint --------------------
    elif page_option == "Edit Sprint":
        st.subheader("Edit Sprint")
        if not df.empty:
            sprint_to_edit = st.selectbox("Select sprint to edit:", df["sprint_name"].tolist(), key="edit_selector")
            current_sprint = df[df["sprint_name"] == sprint_to_edit].iloc[0]

            with st.form("edit_sprint_form"):
                st.text_input("Sprint Name", value=current_sprint["sprint_name"], disabled=True)
                edit_sprint_capacity = st.number_input(
                    "Sprint Capacity", min_value=0, step=1,
                    value=int(current_sprint["sprint_capacity"]) if current_sprint["sprint_capacity"] else 0
                )
                edit_submitted = st.form_submit_button("Update Sprint")

                if edit_submitted:
                    try:
                        with conn.session as session:
                            session.execute(
                                text("""
                                    UPDATE sprint_info
                                    SET sprint_capacity = :sprint_capacity
                                    WHERE sprint_name = :sprint_name
                                """),
                                {
                                    "sprint_name": sprint_to_edit,
                                    "sprint_capacity": edit_sprint_capacity
                                }
                            )
                            session.commit()
                            get_data.clear()
                        st.success(f"Sprint {sprint_to_edit} updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating sprint: {str(e)}")

    # -------------------- Delete Sprint --------------------
    elif page_option == "Delete Sprint":
        st.subheader("Delete Sprint")
        if not df.empty:
            sprint_to_delete = st.selectbox("Select sprint to delete:", df["sprint_name"].tolist())
            if st.button("Delete sprint"):
                with conn.session as session:
                    session.execute(
                        text("DELETE FROM sprint_info WHERE sprint_name = :sprint_name"),
                        {"sprint_name": sprint_to_delete}
                    )
                    session.commit()
                    get_data.clear()
                st.success(f"Deleted sprint: {sprint_to_delete}")
                st.rerun()
