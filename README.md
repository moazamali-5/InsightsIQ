# InsightIQ — AI-Powered Business Intelligence & Analytics Platform

A professional, self-contained business analytics web application built with **Streamlit**, **Pandas**, **Plotly** and **OpenPyXL**. Upload CSV or Excel files, explore your data with interactive charts, and assess data quality — all locally, with no API keys or paid services required.

## Features

- Professional dark navy & blue dashboard theme with metric cards and clean typography
- Sidebar navigation: Overview, Upload Dataset, Data Preview, Data Quality, Data Cleaning Studio, Analytics Dashboard, Reports, Professional Reports, Settings
- CSV / Excel (.xlsx) upload with automatic sheet selection for Excel workbooks
- Automatic delimiter and encoding detection for CSV files
- Row/column counts, missing values, duplicates, column types and memory usage
- Interactive scrollable data preview with adjustable row count
- Column profiling (data type, nulls, unique values)
- Data-quality score with plain-language findings and detected issues
- Interactive Plotly charts: histograms, bar charts, scatter plots and line charts
- Correlation detection between numeric columns
- CSV export of the loaded dataset
- Professional, data-driven PDF and five-worksheet Excel reports, using either the original upload or current working dataset
- Display preferences and settings

## Tech stack

- Python 3.10+
- Streamlit
- Pandas
- Plotly
- OpenPyXL

No external AI APIs or API keys are used.

## Project structure

```
InsightIQ/
├── app.py                 # Streamlit entry point
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── .streamlit/
│   └── config.toml        # Streamlit theme & server settings
└── src/
    ├── __init__.py
    ├── config.py          # App identity, navigation, colour palette
    ├── data_loader.py     # CSV/Excel reading with friendly error handling
    ├── state.py           # Session-state (page, dataset, settings) helpers
    ├── theme.py           # Shared CSS + reusable UI components
    ├── utils.py           # Formatting helpers
    ├── analysis.py        # Data profiling & analytics (computed from data only)
    ├── professional_report.py # Data-driven report content and PDF/Excel export
    └── views/
        ├── __init__.py
        ├── overview.py
        ├── upload_dataset.py
        ├── data_preview.py
        ├── data_quality.py
        ├── analytics_dashboard.py
        ├── reports.py
        ├── professional_reports.py
        └── settings.py
```

## Professional reports

Open **Professional Reports** from the sidebar, select either the current working
dataset or the original upload, then select **Generate Report**. The page builds
a PDF with findings, recommendations, tables and suitable dataset charts, plus
an Excel workbook with Dataset Overview, Data Quality, Statistical Summary,
Key Findings and Cleaned Dataset worksheets. The workbook's dataset sheet
contains the data for the selected scope. Report generation is read-only; it
does not modify the uploaded data or cleaning history.

## Installation

Create and activate a virtual environment (recommended), then install dependencies:

```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the app

From the project folder:

```powershell
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.

## Notes

- Files are read into memory only; nothing is written to disk or sent to an external service.
- Large scatter plots are sampled to keep the UI responsive.
- Categorical columns with more than 50 distinct values are not used in bar charts by default (adjustable in Settings).
- Invalid files, empty files and datasets with no data rows are handled with friendly error messages.

## License

MIT