CREATE TABLE IF NOT EXISTS imd_master_history (
    year INT NOT NULL,
    month INT NOT NULL,
    imd_normal_mm NUMERIC(8,2) NOT NULL,
    imd_actual_mm NUMERIC(8,2) NOT NULL,
    actual_l_per_m2 NUMERIC(8,2) NOT NULL,
    actual_scale_1_10 INT NOT NULL,
    PRIMARY KEY (year, month)
);

CREATE TABLE IF NOT EXISTS kurma_sectors_dams (
    sector_id INT PRIMARY KEY,
    sector_name VARCHAR(120) NOT NULL,
    nakshatras VARCHAR(120) NOT NULL,
    river_basins TEXT NOT NULL,
    major_dams TEXT NOT NULL,
    monthly_normals_mm JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS rainfall_predictions (
    year INT NOT NULL,
    month INT NOT NULL,
    sector_id INT NOT NULL,
    score_1_to_10 INT NOT NULL,
    predicted_mm NUMERIC(8,2) NOT NULL,
    predicted_l_per_m2 NUMERIC(8,2) NOT NULL,
    departure_pct NUMERIC(6,2) NOT NULL,
    astro_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (year, month, sector_id)
);
