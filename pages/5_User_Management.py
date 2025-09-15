import streamlit as st
import time
from utils.auth import require_role, _hash_password, login_form
from utils.getter import get_user_data
login_form()

@require_role(["admin"])
def create_account_page():
    st.set_page_config(page_title="User Management", page_icon="👤")
    st.title("Create New User Account")
    # st.info("Only admins can create new accounts and assign roles.")
    conn = st.connection("neon", type="sql")

    with st.form("create_user_form"):
        email = st.text_input("Email")
        username = st.selectbox("Username", options=get_user_data())
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["admin", "manager"])
        submitted = st.form_submit_button("Create Account", type="primary")

        if submitted:
            if not email or not password or not username:
                st.error("Please fill in all fields!")
            else:
                password_hash = _hash_password(password)
                try:
                    from sqlalchemy import text
                    with conn.session as session:
                        session.execute(
                            text("""
                                INSERT INTO app_users (email, username, password, role)
                                VALUES (:email, :username, :password, :role)
                                ON CONFLICT (email) DO UPDATE
                                SET username = EXCLUDED.username, password = EXCLUDED.password, role = EXCLUDED.role
                            """),
                            {"email": email, "username": username, "password": password_hash, "role": role}
                        )
                        session.commit()
                    st.success(f"Successfully created account for {email}!")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating account: {e}")

    st.header("Update/Delete User Account")
    users_df = conn.query("SELECT email, username, role FROM app_users ORDER BY email")
    if not users_df.empty:
        selected_email = st.selectbox("Select user to update/delete:", users_df["email"].tolist(), key="update_user")
        current_user = users_df[users_df["email"] == selected_email].iloc[0]
        with st.form("update_user_form"):
            new_username = st.text_input("Username", value=current_user["username"])
            new_role = st.selectbox("Role", ["admin", "manager"], index=["admin", "manager"].index(current_user["role"]))
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            update_submitted = st.form_submit_button("Update Account", type="primary")
            delete_submitted = st.form_submit_button("Delete Account", type="secondary")
            if update_submitted:
                try:
                    from sqlalchemy import text
                    with conn.session as session:
                        if new_password:
                            password_hash = _hash_password(new_password)
                            session.execute(
                                text("""
                                    UPDATE app_users SET username = :username, role = :role, password = :password WHERE email = :email
                                """),
                                {"username": new_username, "role": new_role, "password": password_hash, "email": selected_email}
                            )
                        else:
                            session.execute(
                                text("""
                                    UPDATE app_users SET username = :username, role = :role WHERE email = :email
                                """),
                                {"username": new_username, "role": new_role, "email": selected_email}
                            )
                        session.commit()
                    st.success(f"Updated account for {selected_email}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating account: {e}")
            if delete_submitted:
                try:
                    from sqlalchemy import text
                    with conn.session as session:
                        session.execute(
                            text("DELETE FROM app_users WHERE email = :email"),
                            {"email": selected_email}
                        )
                        session.commit()
                    st.success(f"Deleted account for {selected_email}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting account: {e}")
    else:
        st.info("No users found.")

create_account_page()
