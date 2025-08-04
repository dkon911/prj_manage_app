drop TABLE project_info;

CREATE TABLE IF NOT EXISTS project_info (
    project_key VARCHAR(20) PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    total_mm integer,
    project_type VARCHAR(50),
    scope VARCHAR(50),
    owner VARCHAR(50),
    start_date DATE,
    end_date DATE,
    status VARCHAR(20),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- sprint info
CREATE TABLE IF NOT EXISTS sprint_info (
    sprint_id VARCHAR PRIMARY KEY,
    sprint_capacity INT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);