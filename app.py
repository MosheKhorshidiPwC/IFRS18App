import io
import re
from typing import List, Dict, Any

import pandas as pd
import plotly.express as px
from rapidfuzz import process, fuzz
import streamlit as st

# --- Configuration ---
st.set_page_config(
    page_title="IFRS 18 P&L Converter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #0068C9; }
    .stButton > button { border-radius: 6px; height: 3em; font-weight: 600; width: 100%; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

# --- Logic Engines ---

def clean_financial_value(x: Any) -> float:
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    if not s or s.lower() in ['nan', '—', '-', '']: return 0.0
    if '(' in s and ')' in s: s = '-' + s.replace('(', '').replace(')', '')
    s = re.sub(r'[^\d\.\-]', '', s)
    try: return float(s)
    except ValueError: return 0.0

def load_data_file(file):
    try:
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    possible_names = ["line item", "description", "account", "label", "caption"]
    line_col = next((c for c in df.columns if c.lower() in possible_names), df.columns[0])
    df = df.rename(columns={line_col: "line item"})
    
    valid_cols = ["line item"]
    for c in df.columns:
        if c == "line item": continue
        clean = str(c).replace(',', '').replace('.', '')
        if len(clean) == 4 and clean.isdigit():
            valid_cols.append(c)
            df[c] = df[c].apply(clean_financial_value)
            
    return df[valid_cols]

def get_ifrs18_data():
    """
    Returns the full schema based on the user's flow chart.
    Separates 'Grouped' (G) lines from 'Detailed' lines.
    """
    
    # 1. The "G" Lines (Grouped / Main Categories)
    grouped_lines = [
        "Revenue from the sale of goods or services",
        "Cost of sales, cost of goods",
        "Sales and marketing",
        "Research and development",
        "General and administrative expenses",
        "Other operating expenses"
    ]

    # 2. The Detailed Lines (Ungrouped / Granular)
    detailed_lines = [
        # Operating Details
        "Depreciation, impairment and impairment reversals of PPE",
        "Amortisation, impairment and impairment reversals of intangibles",
        "Gains and losses on disposal of PPE or intangibles",
        "Foreign exchange differences (Trade Receivables/Payables)",
        "Government grants related to operations",
        "Impairment losses/reversals on trade receivables",
        "Rental income from investment property",
        "Fair value gains/losses from investment property",
        "Bank fees not related to specific borrowing",
        "Gain/loss on lease modifications (ROU)",
        "Variable lease payments",
        "Depreciation of ROU",
        
        # Investing Details
        "Interest income from loans granted to third parties",
        "Share of profit/loss from associates (equity method)",
        "Impairment losses on equity-accounted investments",
        "Dividends from associates (equity method)",
        "Dividends received from investment entities",
        
        # Financing Details
        "Interest expense on lease liability",
        "Interest expense (General)",
        "FX differences on financing debt",
        "Fair value changes on derivatives (Financing)",
        "Net interest expense on net defined benefit liability",
        "FX on lease liabilities",
        
        # Other
        "Income tax expense (benefit)",
        "Discontinued operations"
    ]
    
    # Lines that might shift based on policy
    policy_lines = [
        "Income and expenses from cash and cash equivalents",
        "Interest on loans/bonds not related to customer financing"
    ]
    
    return grouped_lines, detailed_lines + policy_lines

def classify_category(line, template_key, policies):
    l = line.lower()
    
    # Policy Checks
    if "cash" in l and "equivalents" in l:
        return "Operating" if policies.get("cash_is_operating") == "Yes" else "Investing"
    if "loans/bonds not related" in l or "non-customer financing" in l:
        return "Operating" if policies.get("finance_is_operating") == "Yes" else "Financing"

    # Standard Rules
    if "revenue" in l or "cost of sales" in l or "sales and marketing" in l or "research" in l or "general and administrative" in l: return "Operating"
    if "tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    
    # Financing
    if "financing" in l or "lease liability" in l or "interest expense" in l: return "Financing"
    
    # Investing
    if "associates" in l or "equity method" in l or "dividends" in l: return "Investing"
    
    # Default fallback for specific template overrides
    if template_key == "Investing Entity" and ("interest income" in l or "fair value" in l): return "Operating"
    if template_key == "Financing Entity" and ("interest income" in l or "impairment" in l): return "Operating"
    
    return "Operating"

# --- UI Steps ---

def render_progress(step_num):
    labels = ["Upload", "Model Selection", "Map", "Redistribute", "Report"]
    st.markdown(f"### Step {step_num}: {labels[step_num-1]}")
    st.progress(step_num / 5)

def step_1_upload():
    render_progress(1)
    st.info("Upload P&L File (Excel/CSV)")
    file = st.file_uploader("", type=['xlsx', 'csv'])
    if file:
        df = load_data_file(file)
        if not df.empty and len(df.columns) > 1:
            st.session_state.uploaded_df = df
            st.success(f"Loaded! Years found: {', '.join([c for c in df.columns if c != 'line item'])}")
            st.dataframe(df.head(), use_container_width=True)
            if st.button("Next: Business Model →"):
                st.session_state.step = 2
                st.rerun()
        else:
            st.error("Invalid file format.")

def step_2_model():
    render_progress(2)
    st.write("Determine Business Model & Accounting Policies.")
    
    q1 = st.radio("1. Does the entity invest in financial assets as a main activity?", ["No", "Yes"], index=0, key="q1")
    q2 = st.radio("2. Does the entity provide financing to customers as a main activity?", ["No", "Yes"], index=0, key="q2")
    
    template = "General Corporate"
    if q1 == "Yes": template = "Investing Entity"
    if q2 == "Yes": template = "Financing Entity"
    
    st.session_state.template_key = template
    st.info(f"**Template:** {template}")
    
    # Policies
    if template == "Financing Entity":
        st.markdown("##### Accounting Policies")
        p1 = st.radio("Classify Cash & Equivalents?", ["Operating", "Investing"], key="p1")
        p2 = st.radio("Classify Non-Customer Financing Interest?", ["Operating", "Financing"], index=1, key="p2")
        st.session_state.policy_cash = "Yes" if p1 == "Operating" else "No"
        st.session_state.policy_finance = "Yes" if p2 == "Operating" else "No"
    else:
        # Default policies for General/Investing
        st.session_state.policy_cash = "No" # Default Investing
        st.session_state.policy_finance = "No" # Default Financing

    col1, col2 = st.columns(2)
    if col1.button("← Back"): st.session_state.step = 1; st.rerun()
    if col2.button("Confirm & Map →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    render_progress(3)
    st.write("Map source lines. **Select 'Yes' to Ungroup** complex lines into granular IFRS 18 details.")
    
    df = st.session_state.uploaded_df
    grouped_lines, detailed_lines = get_ifrs18_data()
    # In mapping step, we usually map to the "Grouped" lines first, plus common detailed ones
    mapping_targets = grouped_lines + detailed_lines 
    
    if "mapping_df" not in st.session_state:
        mapping = []
        for line in df["line item"]:
            best, _, _ = process.extractOne(str(line), mapping_targets, scorer=fuzz.token_sort_ratio)
            mapping.append({"uploaded_line": line, "target_line": best, "Ungroup": "No"})
        st.session_state.mapping_df = pd.DataFrame(mapping)

    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "target_line": st.column_config.SelectboxColumn("IFRS 18 Target", options=mapping_targets),
            "Ungroup": st.column_config.SelectboxColumn("Ungroup?", options=["No", "Yes"])
        },
        use_container_width=True,
        hide_index=True,
        key="map_editor"
    )
    st.session_state.mapping_df = edited
    
    col1, col2 = st.columns(2)
    if col1.button("← Back"): st.session_state.step = 2; st.rerun()
    
    has_ungroup = any(edited["Ungroup"] == "Yes")
    lbl = "Next: Redistribute →" if has_ungroup else "Next: Report →"
    if col2.button(lbl):
        st.session_state.step = 4 if has_ungroup else 5
        st.rerun()

def step_4_redistribute():
    render_progress(4)
    st.markdown("### Ungroup & Redistribute")
    st.info("Split grouped lines into granular IFRS 18 accounts.")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    grouped_lines, detailed_lines = get_ifrs18_data()
    # When ungrouping, user likely wants the DETAILED list
    target_options = detailed_lines + grouped_lines 
    year_cols = [c for c in df.columns if c != "line item"]
    
    ungroup_rows = mapping[mapping["Ungroup"] == "Yes"]
    if ungroup_rows.empty: st.session_state.step = 5; st.rerun()
    
    alloc_list = []
    tabs = st.tabs([f"📝 {r['uploaded_line']}" for _, r in ungroup_rows.iterrows()])
    
    for i, tab in enumerate(tabs):
        with tab:
            row = ungroup_rows.iloc[i]
            src = row['uploaded_line']
            orig_vals = df[df["line item"] == src].iloc[0][year_cols]
            
            st.write(f"**Original Balance:** " + " | ".join([f"{y}: {orig_vals[y]:,.0f}" for y in year_cols]))
            
            key = f"alloc_df_{i}"
            if key not in st.session_state:
                st.session_state[key] = pd.DataFrame([{"New IFRS Line": target_options[0], **{y: 0.0 for y in year_cols}}])
                
            edited = st.data_editor(
                st.session_state[key],
                column_config={"New IFRS Line": st.column_config.SelectboxColumn(options=target_options)},
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{i}"
            )
            st.session_state[key] = edited
            
            # Validation
            diffs = orig_vals - edited[year_cols].sum()
            cols = st.columns(len(year_cols))
            for idx, y in enumerate(year_cols):
                if abs(diffs[y]) < 1: cols[idx].success(f"{y} OK")
                else: cols[idx].error(f"{y} Rem: {diffs[y]:,.0f}")
                
            res = edited.copy()
            res["_source"] = src
            alloc_list.append(res)

    col1, col2 = st.columns(2)
    if col1.button("← Back"): st.session_state.step = 3; st.rerun()
    if col2.button("Finalize →"):
        st.session_state.final_alloc = pd.concat(alloc_list) if alloc_list else pd.DataFrame()
        st.session_state.step = 5
        st.rerun()

def step_5_report():
    render_progress(5)
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    allocs = st.session_state.get("final_alloc", pd.DataFrame())
    year_cols = [c for c in df.columns if c != "line item"]
    template_key = st.session_state.template_key
    
    policies = {
        "cash_is_operating": st.session_state.get("policy_cash", "No"),
        "finance_is_operating": st.session_state.get("policy_finance", "No")
    }

    # Build Master List
    g_lines, d_lines = get_ifrs18_data()
    all_lines = sorted(list(set(g_lines + d_lines))) # Deduplicate
    
    final = pd.DataFrame({"line item": all_lines})
    final["Category"] = final["line item"].apply(lambda x: classify_category(x, template_key, policies))
    final = final.set_index("line item")
    for y in year_cols: final[y] = 0.0
    
    changes = []
    
    # 1. Standard
    for _, m in mapping.iterrows():
        if m["Ungroup"] == "No":
            src, target = m["uploaded_line"], m["target_line"]
            vals = df[df["line item"] == src].iloc[0][year_cols]
            if target in final.index:
                for y in year_cols: final.at[target, y] += vals[y]
                changes.append({"Source": src, "Action": "Mapped", "Target": target, "Amount": vals[year_cols[0]]})

    # 2. Ungrouped
    if not allocs.empty:
        for src, group in allocs.groupby("_source"):
            orig = df[df["line item"] == src].iloc[0][year_cols]
            allocated_sum = pd.Series(0.0, index=year_cols)
            for _, r in group.iterrows():
                target = r["New IFRS Line"]
                if target in final.index:
                    for y in year_cols: 
                        final.at[target, y] += r[y]
                        allocated_sum[y] += r[y]
                    changes.append({"Source": src, "Action": "Split", "Target": target, "Amount": r[year_cols[0]]})
            
            # Remainder
            rem = orig - allocated_sum
            if rem.abs().sum() > 1:
                 def_target = mapping[mapping["uploaded_line"]==src]["target_line"].values[0]
                 if def_target in final.index:
                     for y in year_cols: final.at[def_target, y] += rem[y]
                     changes.append({"Source": src, "Action": "Remainder", "Target": def_target, "Amount": rem[year_cols[0]]})

    # Display
    final = final.reset_index()
    final = final[final[year_cols].abs().sum(axis=1) > 0] # Filter empty rows
    
    order = {"Operating": 1, "Investing": 2, "Financing": 3, "Income Tax": 4, "Discontinued Ops": 5}
    final["order"] = final["Category"].map(order).fillna(99)
    final = final.sort_values(["order", "line item"]).drop(columns=["order"])
    
    t1, t2 = st.tabs(["Final P&L", "Changes Ledger"])
    with t1:
        st.dataframe(final.style.format({y: "{:,.0f}" for y in year_cols}), use_container_width=True, height=600)
    with t2:
        st.dataframe(pd.DataFrame(changes), use_container_width=True)

    if st.button("Restart"): st.session_state.clear(); st.rerun()

# --- Main ---
if "step" not in st.session_state: st.session_state.step = 1
if st.session_state.step == 1: step_1_upload()
elif st.session_state.step == 2: step_2_model()
elif st.session_state.step == 3: step_3_map()
elif st.session_state.step == 4: step_4_redistribute()
elif st.session_state.step == 5: step_5_report()
