import io
from typing import Dict, List
import numpy as np
import pandas as pd
import streamlit as st

from data_loader import (
    MAX_FILE_SIZE_MB,
    clean_numeric_series,
    guess_column_mapping,
    read_trial_balance,
    
)
from models import IFRSCategory, LineItem, MappingConfig, UploadedTBColumns
from mapping import apply_line_item_mapping
from pl_generator import generate_ifrs18_pl
from currency import SUPPORTED_CURRENCIES


st.set_page_config(page_title="IFRS 18 P&L Prototype", layout="wide")
st.title("IFRS 18 Profit & Loss Prototype")
st.caption(
    "Upload a Trial Balance, map columns and GL prefixes to line items, and generate an IFRS 18 P&L with required subtotals."
)

with st.sidebar:
    st.header("Settings")
    uploaded_currency = st.selectbox(
        "Trial Balance Currency",
        options=SUPPORTED_CURRENCIES,
        index=SUPPORTED_CURRENCIES.index("ILS") if "ILS" in SUPPORTED_CURRENCIES else 0,
        help="Select the currency of the uploaded trial balance amounts.",
    )
    st.info(
        "The prototype does not perform FX conversion. Amounts are displayed in the uploaded currency.",
        icon="ℹ️",
    )

st.subheader("1) Upload Trial Balance")
uploaded_file = st.file_uploader(
    "Upload CSV or XLSX",
    type=["csv", "xlsx"],
    help=f"Max file size ~{MAX_FILE_SIZE_MB} MB",
)

# Line items configuration
DEFAULT_LINE_ITEMS = [
    "Revenue",
    "Cost Of Goods",
    "General and Administrative Expenses",
]
FIXED_LINE_ITEMS = DEFAULT_LINE_ITEMS + [
    "Impairment of Goodwill",
]

if "mapping_df" not in st.session_state:
    default_rows = [
        {"line_item": name, "gl_prefixes": "", "prefix_length": 0}
        for name in DEFAULT_LINE_ITEMS
    ]
    st.session_state.mapping_df = pd.DataFrame(default_rows)

if "mapping_saved" not in st.session_state:
    st.session_state.mapping_saved = False

trial_balance_df: pd.DataFrame | None = None
column_mapping: UploadedTBColumns | None = None
record_count: int | None = None

if uploaded_file is not None:
    try:
        trial_balance_df = read_trial_balance(uploaded_file, uploaded_file.name)
        record_count = len(trial_balance_df)
        st.success(f"Loaded {record_count} rows from file: {uploaded_file.name}")

        st.subheader("2) Map Columns")
        inferred = guess_column_mapping(list(trial_balance_df.columns))
        c1, c2, c3 = st.columns(3)
        with c1:
            account_col = st.selectbox(
                "Account Number column",
                options=list(trial_balance_df.columns),
                index=max(0, list(trial_balance_df.columns).index(inferred.get("account", trial_balance_df.columns[0]))),
            )
        with c2:
            debit_col = st.selectbox(
                "Debit Amount column",
                options=list(trial_balance_df.columns),
                index=max(0, list(trial_balance_df.columns).index(inferred.get("debit", trial_balance_df.columns[0]))),
            )
        with c3:
            credit_col = st.selectbox(
                "Credit Amount column",
                options=list(trial_balance_df.columns),
                index=max(0, list(trial_balance_df.columns).index(inferred.get("credit", trial_balance_df.columns[0]))),
            )
        column_mapping = UploadedTBColumns(
            account_col=account_col,
            debit_col=debit_col,
            credit_col=credit_col,
        )

        # Clean numeric columns safely
        df = trial_balance_df.copy()
        df[column_mapping.debit_col] = clean_numeric_series(df[column_mapping.debit_col])
        df[column_mapping.credit_col] = clean_numeric_series(df[column_mapping.credit_col])

        st.subheader("3) Define Line-Item to GL Prefix Mapping")
        st.caption("Edit the mapping below. Add or remove rows directly in the table, then click Save.")

        with st.form("mapping_form", clear_on_submit=False):
            edited_mapping = st.data_editor(
                st.session_state.mapping_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "line_item": st.column_config.SelectboxColumn(
                        "Line Item",
                        options=FIXED_LINE_ITEMS,
                    ),
                    "gl_prefixes": st.column_config.TextColumn(
                        "GL Account Prefixes (comma-separated)",
                    ),
                    "prefix_length": st.column_config.NumberColumn(
                        "Prefix Length",
                        min_value=0,
                        max_value=20,
                        step=1,
                    ),
                },
                key="mapping_editor",
            )
            save_clicked = st.form_submit_button("Save mapping", type="primary")

        if save_clicked:
            st.session_state.mapping_df = edited_mapping.copy()
            st.session_state.mapping_saved = True
            st.success("Mapping saved. You can now generate the report.")
        else:
            # If user edits without saving, keep edits visible but require save to generate
            st.session_state.mapping_saved = False
        # Check if the mapping is saved
        if not st.session_state.mapping_saved:
            st.info("Save the mapping to enable 'Generate P&L'.")

        st.subheader("4) Generate Profit & Loss (IFRS 18)")
        generate_disabled = not st.session_state.mapping_saved
        if st.button("Generate P&L", type="primary", disabled=generate_disabled):
            # Validate: require prefixes on all mapping rows to avoid unintended empty classifications
            empty_mask = st.session_state.mapping_df["gl_prefixes"].fillna("").astype(str).str.strip() == ""
            if empty_mask.any():
                empty_items = st.session_state.mapping_df.loc[empty_mask, "line_item"].astype(str).tolist()
                st.info(
                    "Some mapping rows have no GL prefixes. Please map or delete these rows before generating: "
                    + ", ".join(empty_items)
                )
                st.stop()

            # Build MappingConfig (default all to OPERATING as these are operating lines)
            line_items: List[LineItem] = []
            for _, row in st.session_state.mapping_df.iterrows():
                prefixes_str: str = str(row.get("gl_prefixes", "")).strip()
                prefixes: List[str] = [p.strip() for p in prefixes_str.split(",") if p.strip()]
                li = LineItem(
                    name=str(row.get("line_item", "")).strip() or "(Unnamed)",
                    gl_prefixes=prefixes,
                    prefix_length=int(row.get("prefix_length", 0) or 0),
                    category=IFRSCategory.OPERATING,
                )
                line_items.append(li)
            mapping_config = MappingConfig(items=line_items)

            mapped_totals = apply_line_item_mapping(
                df=df,
                account_col=column_mapping.account_col,
                debit_col=column_mapping.debit_col,
                credit_col=column_mapping.credit_col,
                mapping=mapping_config,
            )

            pl_df = generate_ifrs18_pl(mapped_totals)

            # Format negatives with brackets and style subtotals
            def _fmt_brackets(x: float) -> str:
                try:
                    val = float(x)
                except Exception:
                    return ""
                if val < 0:
                    return f"({abs(val):,.2f})"
                return f"{val:,.2f}"

            full_df = pl_df[["label", "amount", "type"]].copy()
            full_df["Amount"] = full_df["amount"].map(_fmt_brackets)
            full_df = full_df[["label", "Amount", "type"]].rename(columns={"label": "Line Item"})

            # Build a view without the helper 'type' column for users
            view_df = full_df[["Line Item", "Amount"]].copy()
            is_subtotal = full_df["type"].eq("subtotal")

            def _row_style_view(row):
                if is_subtotal.loc[row.name]:
                    return ["background-color: #f0f0f0; font-weight: bold;"] * len(row)
                return [""] * len(row)

            styler = view_df.style.apply(_row_style_view, axis=1)
            # Make Amount column bold for all rows
            try:
                styler = styler.set_properties(subset=["Amount"], **{"font-weight": "bold"})
            except Exception:
                pass

            st.markdown(f"### Profit and Loss Statement ({uploaded_currency})")
            st.dataframe(styler, use_container_width=True)

            csv_bytes = pl_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download P&L as CSV",
                data=csv_bytes,
                file_name="profit_and_loss_csv",
                mime="text/csv",
            )

    except Exception as exc:
        st.error(f"Failed to process file: {exc}")
        st.stop()

st.divider()
st.caption(
    "Prototype for demonstration. Validate outputs against your accounting policies and IFRS 18."
)
