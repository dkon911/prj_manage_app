from datetime import datetime
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy as sa
import os
from dotenv import load_dotenv
 
st.title("Presales Importer")
st.write("Upload your Excel file to import presales deals into the database.")
 
load_dotenv()
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_HOST = os.getenv("PG_HOST")
PG_DB = os.getenv("PG_DB")
PG_PORT = os.getenv("PG_PORT", 5432)
 
def load_dim_table(df: pd.DataFrame, table_name: str, if_exists="append"):
    """Load data into a dimension table in PostgreSQL.
 
    Args:
        df (pd.DataFrame): DataFrame containing the data to load.
        table_name (str): Name of the target table in PostgreSQL.
        if_exists (str, optional): Behavior when the table already exists. Defaults to "append".
    """
    engine = create_engine(f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    try:
        print(f"PostgreSQL connect success.")
        df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        print(f"Write to table {table_name} successfully")
    except Exception as e:
        print(f"❌ Error {table_name}:", e)
       
def upsert_dataframe_to_table(df, table_name, unique_column):
        """
        Perform an upsert operation (insert or update) for a DataFrame to a database table.
 
        Args:
            df (DataFrame): The DataFrame to load
            table_name (str): The name of the table
            unique_column (str): The unique column name (e.g., 'name')
 
        Returns:
            tuple: (Number of inserted records, Number of updated records)
        """
        if df.empty:
            return 0, 0
        engine = create_engine(f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}")
        print(f"PostgreSQL connect success.")
        try:
            with engine.begin() as connection:
                # Get existing records from the database
                query = f"SELECT {unique_column} FROM {table_name}"
                existing_records = pd.read_sql(query, connection)
 
                existing_values = set(existing_records[unique_column].values) if not existing_records.empty else set()
                df_values = set(df[unique_column].values)
 
                to_update_values = df_values.intersection(existing_values)
                to_insert_values = df_values - existing_values
 
                to_update_df = df[df[unique_column].isin(to_update_values)]
                to_insert_df = df[df[unique_column].isin(to_insert_values)]
 
                # Handle updates
                for _, row in to_update_df.iterrows():
                    # Lấy các cột ngoài unique_column
                    update_columns = [col for col in row.index if col != unique_column]
                    if not update_columns:
                        continue  # Bỏ qua nếu không có cột nào để update
 
                    set_clauses = [f"{col} = :{col}" for col in update_columns]
                    params = {col: (row[col] if pd.notna(row[col]) else None) for col in update_columns}
                    params[unique_column] = row[unique_column]
 
                    update_sql = f"""
                        UPDATE {table_name}
                        SET {', '.join(set_clauses)}
                        WHERE {unique_column} = :{unique_column}
                    """
                    connection.execute(sa.text(update_sql), params)
 
                # Handle inserts
                if not to_insert_df.empty:
                    to_insert_df = to_insert_df.where(pd.notna(to_insert_df), None)
                    to_insert_df.to_sql(
                        name=table_name,
                        con=connection,
                        if_exists='append',
                        index=False
                    )
 
                return len(to_insert_df), len(to_update_df)
        except Exception as e:
            print(f"❌ Error upserting to {table_name}: {e}")
            return 0, 0
 
 
uploaded_file = st.file_uploader("Drag and drop Excel file here", type=["xlsx"])
 
if uploaded_file:
    try:
        # Read Excel file
        df = pd.read_excel(uploaded_file, sheet_name="Official Deal", header=1)
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Deal Name'], how='any')
        # Select and rename columns
        df = df[[
            'Deal Name', 'Project Type', 'Deal Amount',
            'Deal Received(MM/DD/YY)', 'Proposal Sent', 'Pending',
            'Lost/Canceled', 'Won',
            'Division', 'Division 1 - %', 'Division 2 - %','Reasons'
        ]]
 
        df = df.rename(columns={
            'Deal Name': 'deal_name',
            'Project Type': 'project_type',
            'Deal Amount': 'deal_amount',
            'Deal Received(MM/DD/YY)': 'deal_received_date',
            'Proposal Sent': 'proposal_sent_date',
            'Lost/Canceled': 'lost_date',
            'Won': 'won_date',
            'Pending': 'pending_date',
            'Division': 'division',
            'Division 1 - %': 'division_1_pct',
            'Division 2 - %': 'division_2_pct',
            'Reasons': 'Reasons'
        })
 
        # Clean date columns
        for col in ['deal_received_date', 'proposal_sent_date', 'pending_date', 'won_date', 'lost_date']:
            df[col] = pd.to_datetime(df[col], errors='coerce')
 
        # Clean deal_amount
        df['deal_amount'] = df['deal_amount'].replace('[\$,]', '', regex=True).astype(float)
 
        # Determine status
        def determine_status(row):
            if pd.notnull(row['won_date']):
                return 'Won'
            if pd.notnull(row['lost_date']):
                return 'Lost'
            if pd.notnull(row['pending_date']):
                return 'Pending'
            if pd.notnull(row['proposal_sent_date']):
                return 'Proposal Sent'
            return 'Preparing Proposal'
 
        df['status'] = df.apply(determine_status, axis=1)
 
        # Add closest date logic for month, week, day, quarter, year
        date_cols = ['won_date', 'pending_date', 'deal_received_date', 'lost_date']
        current_date = datetime.now()
 
        def get_closest_date_info(row):
            """
            Tìm ngày gần với ngày hiện tại nhất và trả về month, week, day, quarter, year
            """
            valid_dates = [d for d in row[date_cols] if pd.notnull(d)]
           
            if not valid_dates:
                return None, None, None, None, None
           
            # Tính khoảng cách từ mỗi ngày đến ngày hiện tại
            closest_date = min(valid_dates, key=lambda x: abs((x - current_date).days))
           
            return (
                closest_date.month,
                closest_date.isocalendar()[1],
                closest_date.day,
                closest_date.quarter,
                closest_date.year
            )
 
        # Áp dụng function để lấy month, week, day, quarter, year gần nhất
        df[['month', 'week', 'day', 'quarter', 'year']] = df.apply(
            lambda row: pd.Series(get_closest_date_info(row)),
            axis=1
        )
 
        # Connect to DB
        db_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
        engine = create_engine(db_url)
 
        # Write to DB
        # upsert_dataframe_to_table(df, "fact_deals", unique_column="deal_name")
        load_dim_table(df, "fact_deals")
        st.dataframe(df.head())
        st.success("✅ ETL Completed: fact_deals updated.")
    except Exception as e:
        st.error(f"❌ Error: {e}")