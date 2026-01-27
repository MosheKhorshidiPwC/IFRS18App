# IFRS 18 P&L Converter 📊

A robust Streamlit application designed to convert standard financial Profit & Loss (P&L) statements into **IFRS 18 compliant presentation formats**. This tool automates business model classification, line item mapping, and granular redistribution of expenses.

## 🚀 Key Features

* **Smart Business Model Detection**:
    * Supports **General Corporate**, **Investing Entity**, and **Financing Entity** models.
    * Includes specific **Accounting Policy** toggles for Financing Entities (e.g., classifying Cash & Equivalents as Operating vs. Investing).
* **Wizard-Style Workflow**:
    * A step-by-step interface (Steps 1-5) that prevents user overwhelm.
    * **Progress Bar** at the top of every screen to track completion.
* **Granular Ungrouping Engine**:
    * Allows users to take "Grouped" lines (e.g., *Operating Expenses*) and split them into detailed IFRS 18 lines (e.g., *Sales & Marketing*, *R&D*, *Depreciation*).
    * Includes real-time **Balance Validation** to ensure the split amounts match the original total.
* **Audit Trail (Changes Ledger)**:
    * Generates a detailed log of every move, showing exactly how source lines were mapped, split, or reclassified.

## 🛠️ Installation

1.  **Clone the repository** or download the source code.
2.  **Install dependencies** using pip:

```bash
pip install -r requirements.txt
