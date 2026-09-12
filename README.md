# AI Sales Intelligence

A streaming data pipeline for turning large internet-observation datasets into account-level sales signals.

## Pipeline

```text
Zstandard NDJSON -> normalized observations -> Parquet -> DuckDB accounts -> deterministic scores -> workflows
```

## Usage

Install dependencies in the project environment:

```powershell
python -m pip install -r requirements.txt
```
## UI Screenshots

### Dashboard
![Dashboard UI](image/ui1.PNG)

### Account Intelligence
![Account Intelligence UI](image/ui2.PNG)

### Sales Signals
![Sales Signals UI](image/ui3.PNG)

### Account Details
![Account Details UI](image/ui4.PNG)

### Workflow
![Workflow UI](image/ui5.PNG)

The AI and Streamlit layers are deliberately isolated from ingestion and deterministic scoring.

## App

```powershell
streamlit run app.py
```

