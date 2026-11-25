-- 1. Check all successfully loaded purchase orders
SELECT * FROM stg_regional_po;

-- 2. Check file processing audit details
SELECT * FROM etl_file_audit_log;

-- 3. Count total records loaded
SELECT COUNT(*) AS total_records
FROM stg_regional_po;

-- 4. Count successful and failed files
SELECT status, COUNT(*) AS total_files
FROM etl_file_audit_log
GROUP BY status;

-- 5. Calculate total purchase order value by region
SELECT
    region,
    SUM(total_po_value) AS total_spend
FROM stg_regional_po
GROUP BY region;