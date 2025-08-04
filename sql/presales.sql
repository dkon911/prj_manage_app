CREATE TABLE if not exists fact_deals (
    deal_id SERIAL PRIMARY KEY,
    deal_name TEXT,
    project_type VARCHAR(50),
    deal_amount NUMERIC,
    deal_received_date DATE,
    proposal_sent_date DATE,
    pending_date DATE,
    lost_date DATE,
    won_date DATE,
    division TEXT,
    division_1_pct NUMERIC,
    division_2_pct NUMERIC,
    status VARCHAR(20),
    quarter INT,
    year INT,
    imported_at TIMESTAMP DEFAULT now()
);

CREATE TABLE if not exists dim_date (
    full_date DATE UNIQUE,
    year INT,
    quarter VARCHAR(2),
    month INT,
    week INT,
    day INT,
    day_name VARCHAR(10)
);
