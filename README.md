# Regional Purchase Order Ingestion Pipeline

## Project Overview

This project implements a multi-file folder ingestion pipeline using Python and SQL.

It dynamically reads multiple regional Purchase Order (PO) CSV files from an incoming folder, validates the data, calculates total purchase order values, and loads valid records into an SQLite staging database.

Invalid files are moved to a rejected folder, while successfully processed files are moved to an archive folder.

The pipeline also maintains an audit log and generates detailed execution logs.

## Technologies Used

- Python
- Pandas
- SQLite
- SQL
- Logging
- ConfigParser

## Project Structure

```text
pharma regional po loader/
│
├── config/
│   ├── config.ini
│   └── config.example.ini
│
├── data/
│   ├── incoming/
│   ├── archive/
│   ├── rejected/
│   └── pharma_po.db
│
├── logs/
│
├── sql/
│   ├── ddl_schema.sql
│   └── verification_queries.sql
│
├── src/
│   └── ingest_regional_po.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Key Features

1. **Multi-file ingestion:** Dynamically discovers CSV files in the incoming folder.
2. **File validation:** Checks for empty files and missing mandatory columns.
3. **Data validation:** Checks required values and numeric fields.
4. **Data enrichment:** Calculates total PO value using quantity and unit price.
5. **Database loading:** Loads valid records into the SQLite staging table.
6. **Audit logging:** Records successful and failed file processing details.
7. **File management:** Moves successful files to archive and invalid files to rejected.
8. **Execution logging:** Generates timestamped logs with detailed processing information.

## Database Tables

### 1. stg_regional_po

Stores validated purchase order records, including:

- PO number
- Region
- Supplier ID
- Material code
- Ordered quantity
- Unit price
- Order date
- Total PO value
- Source filename
- Loaded timestamp

### 2. etl_file_audit_log

Maintains file processing information:

- File name
- Number of rows loaded
- Processing status
- Error message
- Processing timestamp

## Installation

Install the required Python dependency:

```bash
pip install -r requirements.txt
```

## Configuration

Update `config/config.ini` with the required folder paths, database location, and logging settings.

A sample configuration is provided in `config.example.ini`.

## Execution

Run the pipeline from the project root directory:

```bash
python src/ingest_regional_po.py
```

## Expected Execution Results

Using the sample input files:

| Metric | Expected Result |
|---|---:|
| Total files processed | 5 |
| Successfully processed | 3 |
| Failed files | 2 |
| Total records loaded | 8 |

## Output

- Valid CSV files are moved to the archive folder.
- Invalid CSV files are moved to the rejected folder.
- Valid records are stored in the SQLite database.
- File processing details are stored in the audit table.
- Detailed execution logs are generated in the logs folder.

## SQL Verification

SQL verification queries are available in:

`sql/verification_queries.sql`

These queries can be used to inspect loaded records, audit information, file processing status, and regional purchase order values.

## Project Outcome

Successfully developed a Python and SQL-based multi-file ingestion pipeline with data validation, database loading, audit logging, error handling, and automated file management.