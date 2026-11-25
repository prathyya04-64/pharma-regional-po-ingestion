###############################################################################
# Script Name    : ingest_regional_po.py
# Objective      : Read multiple regional purchase order CSV files, validate
#                  the data, calculate purchase order values, load valid
#                  records into SQLite, move invalid files to rejected,
#                  archive successful files, and maintain audit logs.
# Created By     : Prathyusha A
# Created Date   : 25/11/2026
# Modified Date  : 25/11/2026
# Modified By    : Prathyusha A
# Comments       : Implements multi-file ingestion and audit logging using
#                  Python, Pandas and SQLite.
###############################################################################

"""
Pseudocode:

Step 1 : Read configuration settings and identify input, archive, rejected and database paths.

Step 2 : Scan the incoming folder and discover all CSV files.

Step 3 : Read each CSV file and validate empty files and mandatory columns.

Step 4 : Validate data, calculate total purchase order value and add source filename and timestamp.

Step 5 : Load valid records into SQLite staging table and maintain audit logs.

Step 6 : Move successfully processed files to the archive folder.

Step 7 : Record errors in the audit log and move invalid files to the rejected folder.

Step 8 : Generate execution logs and complete the ingestion process.

"""

import pandas as pd
import sqlite3
import logging
import configparser
import shutil

from pathlib import Path
from datetime import datetime


# --------------------------------------------------
# 1. PROJECT PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = BASE_DIR / "config" / "config.ini"


# --------------------------------------------------
# 2. READ CONFIGURATION
# --------------------------------------------------

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

incoming_dir = BASE_DIR / config["paths"]["incoming_dir"]
archive_dir = BASE_DIR / config["paths"]["archive_dir"]
rejected_dir = BASE_DIR / config["paths"]["rejected_dir"]

db_path = BASE_DIR / config["database"]["db_path"]

log_dir = BASE_DIR / config["logging"]["log_dir"]
log_file = config["logging"]["log_file"]
log_level = config["logging"]["log_level"]


# --------------------------------------------------
# 3. CREATE REQUIRED FOLDERS
# --------------------------------------------------

incoming_dir.mkdir(parents=True, exist_ok=True)
archive_dir.mkdir(parents=True, exist_ok=True)
rejected_dir.mkdir(parents=True, exist_ok=True)
db_path.parent.mkdir(parents=True, exist_ok=True)
log_dir.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 4. SET UP LOGGING
# --------------------------------------------------

# Generate timestamp for log filename
RUN_START = datetime.now()

log_filename = (
    f"regional_po_ingestion_{RUN_START.strftime('%Y%m%d_%H%M%S')}.log"
)

logging.basicConfig(
    filename=log_dir / log_filename,
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    force=True
)

logger = logging.getLogger(__name__)

# Log script start
logger.info(
    f"ingest_regional_po.py started at "
    f"{RUN_START.strftime('%d/%m/%Y %H:%M:%S')}"
)
logger.info("")
logger.info("Project configuration loaded successfully.")
logger.info(f"Log file: {log_filename}")

logger.info(f"Incoming directory: {incoming_dir}")
logger.info(f"Archive directory: {archive_dir}")
logger.info(f"Rejected directory: {rejected_dir}")
logger.info(f"Database path: {db_path}")
logger.info("Logging initialized successfully.")
logger.info("")


# --------------------------------------------------
# 5. DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    return sqlite3.connect(db_path)


# --------------------------------------------------
# 6. CREATE DATABASE TABLES
# --------------------------------------------------

def create_tables():

    logger.info("Database schema initialization started.")

    sql_file = BASE_DIR / "sql" / "ddl_schema.sql"

    logger.info(f"Reading SQL schema file: {sql_file.name}")

    with open(sql_file, "r", encoding="utf-8") as file:
        sql_script = file.read()

    logger.info("SQL schema file read successfully.")

    conn = get_db_connection()

    try:
        logger.info("Database connection established successfully.")

        conn.executescript(sql_script)
        conn.commit()

        logger.info("Database tables created successfully.")

    finally:
        conn.close()
        logger.info("Database connection closed.")
        logger.info("")

# --------------------------------------------------
# 7. REQUIRED COLUMN VALIDATION
# --------------------------------------------------

REQUIRED_COLUMNS = [
    "po_number",
    "region",
    "supplier_id",
    "material_code",
    "ordered_qty",
    "unit_price_usd",
    "order_date"
]


def validate_file(file_path):

    # Check whether the file is empty
    if file_path.stat().st_size == 0:
        raise ValueError("CSV file is empty")

    # Read CSV file
    df = pd.read_csv(file_path)

    # Check whether the CSV contains records
    if df.empty:
        raise ValueError("CSV file contains no records")

    # Check mandatory columns
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing mandatory columns: {missing_columns}"
        )

    # Validate numeric columns
    df["ordered_qty"] = pd.to_numeric(
        df["ordered_qty"], errors="raise"
    )

    df["unit_price_usd"] = pd.to_numeric(
        df["unit_price_usd"], errors="raise"
    )

    if df[["ordered_qty", "unit_price_usd"]].isnull().any().any():
        raise ValueError("Quantity or unit price contains NULL values")

    return df


# --------------------------------------------------
# 8. PROCESS AND LOAD VALID DATA
# --------------------------------------------------

def load_data(df, file_name):

    loaded_at = datetime.now().isoformat(timespec="seconds")

    # Calculate total purchase order value
    df["total_po_value"] = (
        df["ordered_qty"] * df["unit_price_usd"]
    )

    # Add source file name
    df["source_file_name"] = file_name

    # Add loading timestamp
    df["loaded_at"] = loaded_at

    columns = [
        "po_number",
        "region",
        "supplier_id",
        "material_code",
        "ordered_qty",
        "unit_price_usd",
        "order_date",
        "total_po_value",
        "source_file_name",
        "loaded_at"
    ]

    df = df[columns]

    return df


# --------------------------------------------------
# 9. INSERT AUDIT LOG
# --------------------------------------------------

def insert_audit_log(
    conn, file_name, rows_loaded, status, error_message
):

    processed_at = datetime.now().isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO etl_file_audit_log
        (file_name, rows_loaded, status, error_message, processed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            file_name,
            rows_loaded,
            status,
            error_message,
            processed_at
        )
    )


# --------------------------------------------------
# 10. PROCESS EACH CSV FILE
# --------------------------------------------------
def process_file(file_path):

    file_name = file_path.name

    logger.info("=" * 60)
    logger.info(f"FILE PROCESSING STARTED: {file_name}")
    logger.info(f"Source location: {file_path}")

    try:

        # Validate CSV file
        logger.info("Step 1: CSV file validation started.")

        df = validate_file(file_path)

        logger.info("CSV file validation completed successfully.")
        logger.info(f"Number of records identified: {len(df)}")

        # Enrich the data
        logger.info("Step 2: Data enrichment started.")

        df = load_data(df, file_name)

        logger.info("Data enrichment completed successfully.")
        logger.info("Total PO value calculated.")

        # Connect to database
        logger.info("Step 3: Database loading started.")

        conn = get_db_connection()

        try:

            with conn:

                df.to_sql(
                    "stg_regional_po",
                    conn,
                    if_exists="append",
                    index=False
                )

                logger.info(
                    f"Successfully inserted {len(df)} records "
                    "into stg_regional_po."
                )

                # Insert successful audit record
                insert_audit_log(
                    conn,
                    file_name,
                    len(df),
                    "SUCCESS",
                    None
                )

                logger.info("SUCCESS audit record inserted.")

        finally:
            conn.close()
            logger.info("Database connection closed.")

        # Move successfully processed file to archive
        logger.info("Step 4: Moving processed file to archive.")

        shutil.move(
            str(file_path),
            str(archive_dir / file_name)
        )

        logger.info(f"File archived successfully: {file_name}")
        logger.info(f"Rows loaded: {len(df)}")
        logger.info(f"FILE PROCESSING COMPLETED: {file_name}")

        return True

    except Exception as error:

        error_message = str(error)

        logger.error(
            f"FILE PROCESSING FAILED: {file_name}"
        )
        logger.error(f"Error details: {error_message}")

        # Record failed file in audit table
        conn = get_db_connection()

        try:
            with conn:
                insert_audit_log(
                    conn,
                    file_name,
                    0,
                    "FAILED",
                    error_message
                )

            logger.info("FAILED audit record inserted.")

        finally:
            conn.close()

        # Move invalid file to rejected folder
        if file_path.exists():

            logger.info("Moving failed file to rejected folder.")

            shutil.move(
                str(file_path),
                str(rejected_dir / file_name)
            )

            logger.info(f"File moved to rejected: {file_name}")

        logger.info(f"FILE PROCESSING ENDED WITH FAILURE: {file_name}")

        return False

    finally:
        logger.info("=" * 60)
        logger.info("")
# --------------------------------------------------
# 11. DISCOVER ALL CSV FILES
# --------------------------------------------------
def process_all_files():

    logger.info("=" * 60)
    logger.info("STARTING REGIONAL PO INGESTION PIPELINE")
    logger.info("=" * 60)

    # Find all CSV files dynamically
    logger.info("Scanning incoming folder for CSV files.")

    csv_files = list(incoming_dir.glob("*.csv"))

    total_files = len(csv_files)
    successful_files = 0
    failed_files = 0
    total_records_loaded = 0

    logger.info(f"Total CSV files discovered: {total_files}")

    if not csv_files:

        logger.info("No CSV files found in incoming folder.")
        return

    # Process each CSV file
    for file_path in csv_files:

        result = process_file(file_path)

        if result:

            successful_files += 1

            # Count records from successfully processed file
            conn = get_db_connection()

            try:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT rows_loaded FROM etl_file_audit_log "
                    "WHERE file_name = ? AND status = 'SUCCESS' "
                    "ORDER BY id DESC LIMIT 1",
                    (file_path.name,)
                )

                row = cursor.fetchone()

                if row:
                    total_records_loaded += row[0]

            finally:
                conn.close()

        else:
            failed_files += 1

    # Execution summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("REGIONAL PO INGESTION EXECUTION SUMMARY")
    logger.info("=" * 60)

    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Successfully processed: {successful_files}")
    logger.info(f"Failed files: {failed_files}")
    logger.info(f"Total records loaded: {total_records_loaded}")

    logger.info("=" * 60)

    logger.info("REGIONAL PO INGESTION PIPELINE COMPLETED")

# --------------------------------------------------
# 12. MAIN FUNCTION
# --------------------------------------------------
def main():

    create_tables()

    logger.info("Database schema initialized successfully.")
    logger.info("")

    process_all_files()

    RUN_END = datetime.now()

    logger.info("")
    logger.info(
        f"ingest_regional_po.py completed at "
        f"{RUN_END.strftime('%d/%m/%Y %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()