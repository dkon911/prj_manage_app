import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine

import os
from dotenv import load_dotenv


load_dotenv()
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_HOST = os.getenv("PG_HOST")
PG_DB = os.getenv("PG_DB")
PG_PORT = os.getenv("PG_PORT", 5432)

db_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
engine = create_engine(db_url)


# Config
start_date = datetime(2020, 1, 1)
end_date = datetime(2030, 12, 31)
dates = pd.date_range(start=start_date, end=end_date)

df = pd.DataFrame({"date": dates})
df["full_date"] = df["date"].dt.strftime("%Y-%m-%d")
df["year"] = df["date"].dt.year
df["quarter"] = df["date"].dt.quarter
df["month"] = df["date"].dt.month
df["week"] = df["date"].dt.isocalendar().week
df["day"] = df["date"].dt.day
df["day_name"] = df["date"].dt.day_name()

# PostgreSQL connection
df.to_sql("dim_date", engine, index=False, if_exists="replace")
print("✅ dim_date created")
