# IFRS 18 Profit & Loss Prototype (Streamlit)

A secure Streamlit prototype that ingests a Trial Balance (CSV/XLSX), lets users map GL account prefixes to IFRS 18 line items, and generates a Profit and Loss statement with mandatory subtotals.

## Quickstart (Windows PowerShell)

```powershell
py -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL shown (e.g., http://localhost:8501) in your browser.

## Features
- Upload CSV/XLSX Trial Balance with robust cleaning/validation
- Column mapping for Account Number, Debit, Credit
- Define line-item to GL account-prefix mapping (with prefix length)
- IFRS 18 categories: operating, investing, financing, income tax, discontinued operations
- Mandatory subtotals (Operating profit, Profit before financing & income tax, Profit before tax, Profit for the period)
- Download P&L as CSV

## Security Notes
- Filetype restrictions (CSV, XLSX), size checks, and strict parsing
- All parsing is done server-side; no external services required
- No files are written to disk; processing in-memory
