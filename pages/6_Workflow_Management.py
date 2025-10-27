import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils.auth import require_role, login_form
from utils.header_nav import header_nav

st.set_page_config(page_title="Workflow Management", page_icon="⚙️", layout="wide")
login_form()

header_nav(current_page="workflow")

@st.cache_data(ttl=10)
def get_workflows(_conn):
    """Fetches all workflows and their associated statuses."""
    try:
        workflows_df = _conn.query("SELECT * FROM workflow ORDER BY workflow_name;", ttl=5)
        statuses_df = _conn.query("SELECT * FROM workflow_status;", ttl=5)
        
        workflow_map = {}
        for _, workflow in workflows_df.iterrows():
            workflow_map[workflow['workflow_id']] = {
                'name': workflow['workflow_name'],
                'statuses': []
            }

        for _, status in statuses_df.iterrows():
            if status['workflow_id'] in workflow_map:
                workflow_map[status['workflow_id']]['statuses'].append({
                    'status_id': status['status_id'],
                    'status_name': status['status_name'],
                    'done_ratio': status['done_ratio']
                })

        return workflow_map
    except Exception as e:
        st.error(f"Error fetching workflows: {e}")
        return {}

@st.cache_data(ttl=60)
def get_status_names(_conn):
    """Fetches all status names from dim_status."""
    try:
        status_df = _conn.query("SELECT status_name FROM dim_status ORDER BY status_name;", ttl=60)
        return status_df['status_name'].tolist()
    except Exception as e:
        st.error(f"Error fetching status names: {e}")
        return []

@require_role(allowed_roles=['admin', 'manager'])
def show_workflow_management():
    """Main function to display the workflow management page."""
    st.title("⚙️ Workflow Management")
    st.write("Create, edit, and manage project workflows and their status-to-done ratios.")

    conn = st.connection("neon", type="sql")

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    # --- Create New Workflow ---
    with st.form("create_workflow_form"):
        st.subheader("➕ Create New Workflow")
        new_workflow_name = st.text_input("Workflow Name")
        submitted = st.form_submit_button("Create")

        if submitted:
            if not new_workflow_name:
                st.warning("Workflow name cannot be empty.")
            else:
                try:
                    with conn.session as s:
                        s.execute(
                            text("INSERT INTO workflow (workflow_name) VALUES (:name) ON CONFLICT (workflow_name) DO NOTHING;"),
                            {"name": new_workflow_name}
                        )
                        s.commit()
                    st.success(f"Workflow '{new_workflow_name}' created or already exists.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating workflow: {e}")
    
    st.markdown("---")

    workflows = get_workflows(conn)
    status_names = get_status_names(conn)

    if not workflows:
        st.info("No workflows found. Create one above.")

    for workflow_id, workflow_data in workflows.items():
        with st.expander(f"**{workflow_data['name']}** (ID: {workflow_id})"):
            
            if workflow_data['statuses']:
                original_statuses = pd.DataFrame(workflow_data['statuses'])
            else:
                # Create an empty DF with the correct columns if no statuses exist
                original_statuses = pd.DataFrame(columns=['status_id', 'status_name', 'done_ratio'])
            
            edited_statuses = st.data_editor(
                original_statuses,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "status_id": None,
                    "status_name": st.column_config.SelectboxColumn(
                        "Status Name",
                        options=status_names,
                        required=True
                    ),
                    "done_ratio": st.column_config.NumberColumn(
                        "Done Ratio (0.0 to 1.0)",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.01,
                        format="%.2f",
                        required=True,
                    ),
                },
                key=f"editor_{workflow_id}"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Statuses", key=f"save_{workflow_id}", type="primary"):
                    try:
                        with conn.session as s:
                            original_ids = set(original_statuses['status_id'].dropna())
                            edited_ids = set(edited_statuses['status_id'].dropna())

                            deleted_ids = original_ids - edited_ids
                            if deleted_ids:
                                s.execute(
                                    text("DELETE FROM workflow_status WHERE status_id = ANY(:ids)"),
                                    {'ids': list(deleted_ids)}
                                )

                            for _, row in edited_statuses.iterrows():
                                status_id = row.get('status_id')
                                status_name = row['status_name']
                                done_ratio = row['done_ratio']

                                if pd.isna(status_id): 
                                    s.execute(
                                        text("INSERT INTO workflow_status (workflow_id, status_name, done_ratio) VALUES (:wid, :name, :ratio) ON CONFLICT (workflow_id, status_name) DO NOTHING;"),
                                        {'wid': workflow_id, 'name': status_name, 'ratio': done_ratio}
                                    )
                                else:
                                    s.execute(
                                        text("UPDATE workflow_status SET status_name = :name, done_ratio = :ratio WHERE status_id = :sid;"),
                                        {'name': status_name, 'ratio': done_ratio, 'sid': status_id}
                                    )
                            s.commit()
                        st.success("Statuses updated successfully!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving statuses: {e}")

            with col2:
                if st.button("🗑️ Delete Workflow", key=f"delete_{workflow_id}"):
                    try:
                        with conn.session as s:
                            s.execute(text("DELETE FROM workflow WHERE workflow_id = :wid;"), {'wid': workflow_id})
                            s.commit()
                        st.success(f"Workflow '{workflow_data['name']}' deleted.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting workflow: {e}")

show_workflow_management()
