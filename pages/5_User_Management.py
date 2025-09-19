import streamlit as st
import time
import re
from utils.auth import require_role, _hash_password, login_form
from utils.getter import get_user_data

# Configure page
st.set_page_config(
    page_title="User Management Dashboard", 
    page_icon="👥", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .form-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .stSelectbox > div > div {
        background-color: white;
    }
    
    .stTextInput > div > div > input {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

login_form()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

@require_role(["admin"])
def create_account_page():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Management Dashboard</h1>
        <p>Create, update, and manage user accounts</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = st.connection("neon", type="sql")
    
    # Sidebar with statistics
    with st.sidebar:
        st.header("📊 Dashboard Stats")
        try:
            users_df = conn.query("SELECT role, COUNT(*) as count FROM app_users GROUP BY role")
            total_users = conn.query("SELECT COUNT(*) as total FROM app_users").iloc[0]['total']
            
            st.metric("Total Users", total_users)
            
            if not users_df.empty:
                for _, row in users_df.iterrows():
                    st.metric(f"{row['role'].title()}s", row['count'])
        except Exception as e:
            st.error(f"Error loading stats: {e}")
    
    # Main content in tabs
    tab1, tab2, tab3 = st.tabs(["➕ Create User", "✏️ Manage Users", "📋 User List"])
    
    with tab1:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Create New User Account")
        
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                email = st.text_input("📧 Email Address", placeholder="user@example.com")
                username = st.selectbox("👤 Username", options=get_user_data())
                
            with col2:
                password = st.text_input("🔒 Password", type="password", help="Min 8 chars, 1 uppercase, 1 lowercase, 1 number")
                confirm_password = st.text_input("🔒 Confirm Password", type="password")
            
            role = st.selectbox("🎭 Role", ["admin", "manager", "pm"], 
                              help="Admin: Full access, Manager: Limited access, PM: Project access only")
            
            # Password strength indicator
            if password:
                is_strong, message = validate_password(password)
                if is_strong:
                    st.success(f"✅ {message}")
                else:
                    st.warning(f"⚠️ {message}")
            
            submitted = st.form_submit_button("🚀 Create Account", type="primary", use_container_width=True)
            
            if submitted:
                # Enhanced validation
                errors = []
                
                if not email or not password or not confirm_password or not username:
                    errors.append("Please fill in all fields!")
                
                if email and not validate_email(email):
                    errors.append("Please enter a valid email address!")
                
                if password != confirm_password:
                    errors.append("Passwords do not match!")
                
                if password:
                    is_strong, message = validate_password(password)
                    if not is_strong:
                        errors.append(message)
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    try:
                        from sqlalchemy import text
                        with conn.session as session:
                            existing = session.execute(
                                text("SELECT 1 FROM app_users WHERE email = :email"),
                                {"email": email}
                            ).fetchone()
                            
                            if existing:
                                st.error(f"❌ Account with email {email} already exists!")
                            else:
                                password_hash = _hash_password(password)
                                session.execute(
                                    text("""
                                        INSERT INTO app_users (email, username, password, role)
                                        VALUES (:email, :username, :password, :role)
                                    """),
                                    {"email": email, "username": username, "password": password_hash, "role": role}
                                )
                                session.commit()
                                st.success(f"✅ Successfully created account for {email}!")
                                st.balloons()
                                time.sleep(2)
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating account: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Update/Delete User Account")
        
        try:
            users_df = conn.query("SELECT email, username, role FROM app_users ORDER BY email")
            
            if not users_df.empty:
                selected_email = st.selectbox("👤 Select user to manage:", users_df["email"].tolist(), key="update_user")
                current_user = users_df[users_df["email"] == selected_email].iloc[0]
                
                # Display current user info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Email:** {current_user['email']}")
                with col2:
                    st.info(f"**Username:** {current_user['username']}")
                with col3:
                    st.info(f"**Role:** {current_user['role'].title()}")
                
                with st.form("update_user_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_username = st.text_input("👤 Username", value=current_user["username"])
                        new_role = st.selectbox("🎭 Role", ["admin", "manager", "pm"], 
                                              index=["admin", "manager", "pm"].index(current_user["role"]))
                    
                    with col2:
                        new_password = st.text_input("🔒 New Password (leave blank to keep current)", type="password")
                        confirm_new_password = st.text_input("🔒 Confirm New Password", type="password") if new_password else ""
                    
                    # Password strength for new password
                    if new_password:
                        is_strong, message = validate_password(new_password)
                        if is_strong:
                            st.success(f"✅ {message}")
                        else:
                            st.warning(f"⚠️ {message}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        update_submitted = st.form_submit_button("✏️ Update Account", type="primary", use_container_width=True)
                    with col2:
                        delete_submitted = st.form_submit_button("🗑️ Delete Account", type="secondary", use_container_width=True)
                    
                    if update_submitted:
                        errors = []
                        
                        if new_password and new_password != confirm_new_password:
                            errors.append("New passwords do not match!")
                        
                        if new_password:
                            is_strong, message = validate_password(new_password)
                            if not is_strong:
                                errors.append(message)
                        
                        if errors:
                            for error in errors:
                                st.error(f"❌ {error}")
                        else:
                            try:
                                from sqlalchemy import text
                                with conn.session as session:
                                    if new_password:
                                        password_hash = _hash_password(new_password)
                                        session.execute(
                                            text("""
                                                UPDATE app_users 
                                                SET username = :username, role = :role, password = :password 
                                                WHERE email = :email
                                            """),
                                            {"username": new_username, "role": new_role, "password": password_hash, "email": selected_email}
                                        )
                                    else:
                                        session.execute(
                                            text("""
                                                UPDATE app_users 
                                                SET username = :username, role = :role 
                                                WHERE email = :email
                                            """),
                                            {"username": new_username, "role": new_role, "email": selected_email}
                                        )
                                    session.commit()
                                st.success(f"✅ Updated account for {selected_email}!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error updating account: {e}")
                    
                    if delete_submitted:
                        # Confirmation dialog
                        if st.session_state.get('confirm_delete') != selected_email:
                            st.session_state.confirm_delete = selected_email
                            st.warning(f"⚠️ Are you sure you want to delete {selected_email}? Click Delete again to confirm.")
                        else:
                            try:
                                from sqlalchemy import text
                                with conn.session as session:
                                    session.execute(
                                        text("DELETE FROM app_users WHERE email = :email"),
                                        {"email": selected_email}
                                    )
                                    session.commit()
                                st.success(f"🗑️ Deleted account for {selected_email}!")
                                del st.session_state.confirm_delete
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting account: {e}")
            else:
                st.info("📭 No users found in the database.")
        except Exception as e:
            st.error(f"❌ Error loading users: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.subheader("📋 All Users")
        
        try:
            users_df = conn.query("SELECT email, username, role FROM app_users ORDER BY role, email")
            
            if not users_df.empty:
                # Add search functionality
                search_term = st.text_input("🔍 Search users", placeholder="Search by email or username...")
                
                if search_term:
                    filtered_df = users_df[
                        users_df['email'].str.contains(search_term, case=False) |
                        users_df['username'].str.contains(search_term, case=False)
                    ]
                else:
                    filtered_df = users_df
                
                # Role filter
                roles = ["All"] + list(users_df['role'].unique())
                selected_role = st.selectbox("Filter by role:", roles)
                
                if selected_role != "All":
                    filtered_df = filtered_df[filtered_df['role'] == selected_role]
                
                # Display results
                st.write(f"Showing {len(filtered_df)} of {len(users_df)} users")
                
                # Enhanced table display
                for idx, user in filtered_df.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.write(f"📧 **{user['email']}**")
                        with col2:
                            st.write(f"👤 {user['username']}")
                        with col3:
                            role_emoji = {"admin": "👑", "manager": "👔", "pm": "📊"}
                            st.write(f"{role_emoji.get(user['role'], '👤')} {user['role'].title()}")
                        with col4:
                            st.write("✅ Active")
                        
                        st.divider()
            else:
                st.info("📭 No users found in the database.")
        except Exception as e:
            st.error(f"❌ Error loading user list: {e}")

create_account_page()
