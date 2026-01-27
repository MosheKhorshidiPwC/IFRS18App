import io
import re
from typing import List, Dict, Any

import pandas as pd
import plotly.express as px
from rapidfuzz import process, fuzz
import streamlit as st

# --- Configuration ---
st.set_page_config(
    page_title="IFRS 18 Converter | PwC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling (PwC / Professional Theme) ---
st.markdown("""
    <style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #ffffff;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2D2D2D;
        font-weight: 700;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f2f2f2;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #D04A02; /* PwC Orange-ish */
        color: white;
        border: none;
        border-radius: 4px;
        height: 3em;
        font-weight: 600;
        width: 100%;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #b03d00;
        color: white;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #D04A02;
    }
    
    /* Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem;
        color: #404040;
    }
    
    /* Tables/Dataframes */
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
    
    /* Logo Container */
    .logo-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .logo-text {
        font-size: 24px;
        font-weight: bold;
        color: #D04A02;
        margin-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper: Logo ---
def render_header():
    col1, col2 = st.columns([1, 5])
    with col1:
        # Use a public URL for the logo or a placeholder
        # In a real deployment, replace this URL with your local file path
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=120)
    with col2:
        st.title("IFRS 18 Financial Statement Converter")
    st.divider()

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
    """Returns 'Grouped' (G) lines and 'Detailed' lines for mapping."""
    grouped_lines = [
        "Revenue from the sale of goods or services", "Cost of sales, cost of goods", 
        "Sales and marketing", "Research and development", 
        "General and administrative expenses", "Other operating expenses"
    ]
    detailed_lines = [
        "Depreciation, impairment of PPE", "Amortisation of intangibles", 
        "Gains/losses on disposal of PPE", "Foreign exchange differences (Trade)", 
        "Government grants (Ops)", "Impairment of trade receivables", 
        "Fair value gains/losses investment property", "Bank fees (non-borrowing)", 
        "Lease modifications (ROU)", "Interest income (3rd party loans)", 
        "Share of profit/loss (Associates)", "Dividends (Associates)", 
        "Interest expense (Leases)", "Interest expense (General)", 
        "FX differences on financing debt", "Fair value changes (Derivatives)", 
        "Income tax expense", "Discontinued operations",
        "Income/expenses from cash & equivalents", "Interest on non-customer financing"
    ]
    return grouped_lines, detailed_lines

def classify_category(line, template_key, policies):
    l = line.lower()
    # Policies
    if "cash" in l and "equivalents" in l:
        return "Operating" if policies.get("cash_is_operating") == "Yes" else "Investing"
    if "non-customer financing" in l or "loans/bonds not related" in l:
        return "Operating" if policies.get("finance_is_operating") == "Yes" else "Financing"

    # Standard
    if any(x in l for x in ["revenue", "cost of sales", "sales and marketing", "research", "general and admin", "operating"]): return "Operating"
    if "tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    if any(x in l for x in ["financing", "lease liability", "interest expense"]): return "Financing"
    if any(x in l for x in ["associates", "equity method", "dividends"]): return "Investing"
    
    # Template Overrides
    if template_key == "Investing Entity" and ("interest income" in l or "fair value" in l): return "Operating"
    if template_key == "Financing Entity" and ("interest income" in l or "impairment" in l): return "Operating"
    
    return "Operating"

# --- State Management Helpers ---

def init_session_state():
    if "step" not in st.session_state: st.session_state.step = 1
    if "template_key" not in st.session_state: st.session_state.template_key = "General Corporate"
    if "policy_cash" not in st.session_state: st.session_state.policy_cash = "No"
    if "policy_finance" not in st.session_state: st.session_state.policy_finance = "No"

# --- UI Steps ---

def render_progress(step_num):
    labels = ["Upload", "Model Selection", "Map", "Redistribute", "Report"]
    st.sidebar.markdown(f"### Current Step: {step_num}")
    st.sidebar.progress(step_num / 5)
    st.sidebar.markdown(f"**{labels[step_num-1]}**")

def step_1_upload():
    render_progress(1)
    st.subheader("Step 1: Upload Financial Data")
    st.info("Upload your P&L (Excel/CSV). Ensure you have a description column and year columns.")
    
    file = st.file_uploader("", type=['xlsx', 'csv'])
    if file:
        df = load_data_file(file)
        if not df.empty and len(df.columns) > 1:
            st.session_state.uploaded_df = df
            st.success(f"Data Loaded! Years detected: {', '.join([c for c in df.columns if c != 'line item'])}")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("Next: Business Model →"):
                st.session_state.step = 2
                st.rerun()
        else:
            st.error("Invalid file format. Please check headers.")

def step_2_model():
    render_progress(2)
    st.subheader("Step 2: Business Model & Policies")
    
    # We use keys for radios so Streamlit manages state automatically (no overwrites)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Investment Activities**")
        q1 = st.radio("Does the entity invest in financial assets as a main activity?", 
                      ["No", "Yes"], index=0, key="q1_invest")
        
    with col2:
        st.markdown("**2. Customer Financing**")
        q2 = st.radio("Does the entity provide financing to customers as a main activity?", 
                      ["No", "Yes"], index=0, key="q2_finance")

    # Determine Template
    template = "General Corporate"
    if q1 == "Yes": template = "Investing Entity"
    if q2 == "Yes": template = "Financing Entity"
    
    st.session_state.template_key = template
    st.success(f"**Determined Model: {template}**")
    
    # Conditional Policies
    if template == "Financing Entity":
        st.divider()
        st.markdown("#### Accounting Policy Choices")
        c1, c2 = st.columns(2)
        with c1:
            p1 = st.radio("Classify Cash & Equivalents?", ["Operating", "Investing"], key="pol_cash")
            st.session_state.policy_cash = "Yes" if p1 == "Operating" else "No"
        with c2:
            p2 = st.radio("Classify Non-Customer Financing Interest?", ["Operating", "Financing"], index=1, key="pol_fin")
            st.session_state.policy_finance = "Yes" if p2 == "Operating" else "No"
    
    st.divider()
    b1, b2 = st.columns([1, 1])
    if b1.button("← Back"): st.session_state.step = 1; st.rerun()
    if b2.button("Confirm & Map →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    render_progress(3)
    st.subheader("Step 3: Line Item Mapping")
    st.write("Match source lines. **Select 'Yes' to Ungroup** complex lines into detailed IFRS 18 accounts.")

    df = st.session_state.uploaded_df
    g_lines, d_lines = get_ifrs18_data()
    # Prioritize Grouped lines for initial mapping
    target_options = g_lines + d_lines
    
    # Initialize mapping ONLY ONCE
    if "mapping_df" not in st.session_state:
        mapping = []
        for line in df["line item"]:
            best, _, _ = process.extractOne(str(line), target_options, scorer=fuzz.token_sort_ratio)
            mapping.append({"uploaded_line": line, "target_line": best, "Ungroup": "No"})
        st.session_state.mapping_df = pd.DataFrame(mapping)

    # The data_editor updates the session_state directly via the key
    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "target_line": st.column_config.SelectboxColumn("IFRS 18 Target", options=target_options),
            "Ungroup": st.column_config.SelectboxColumn("Ungroup?", options=["No", "Yes"])
        },
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor_step3" # Crucial for state persistence
    )
    
    # Manually ensure the state is synced (double safety)
    st.session_state.mapping_df = edited
    
    b1, b2 = st.columns([1, 1])
    if b1.button("← Back"): st.session_state.step = 2; st.rerun()
    
    has_ungroup = any(edited["Ungroup"] == "Yes")
    lbl = "Next: Redistribute Amounts →" if has_ungroup else "Next: Generate Report →"
    
    if b2.button(lbl):
        st.session_state.step = 4 if has_ungroup else 5
        st.rerun()

def step_4_redistribute():
    render_progress(4)
    st.subheader("Step 4: Redistribute & Split")
    st.info("Split grouped lines into granular IFRS 18 details.")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    g_lines, d_lines = get_ifrs18_data()
    target_options = d_lines + g_lines # Prioritize detailed lines for ungrouping
    year_cols = [c for c in df.columns if c != "line item"]
    
    ungroup_rows = mapping[mapping["Ungroup"] == "Yes"]
    if ungroup_rows.empty: st.session_state.step = 5; st.rerun()
    
    # Storage for allocations
    if "alloc_storage" not in st.session_state:
        st.session_state.alloc_storage = {}

    tabs = st.tabs([f"📝 {r['uploaded_line']}" for _, r in ungroup_rows.iterrows()])
    
    alloc_list = []
    
    for i, tab in enumerate(tabs):
        with tab:
            row = ungroup_rows.iloc[i]
            src = row['uploaded_line']
            orig_vals = df[df["line item"] == src].iloc[0][year_cols]
            
            st.caption(f"Original Balance: " + " | ".join([f"{y}: {orig_vals[y]:,.0f}" for y in year_cols]))
            
            # Use unique key per source line to persist data
            storage_key = f"alloc_df_{i}_{src}"
            
            if storage_key not in st.session_state:
                # Initial default row
                st.session_state[storage_key] = pd.DataFrame([{"New IFRS Line": target_options[0], **{y: 0.0 for y in year_cols}}])
            
            # Editor
            edited_alloc = st.data_editor(
                st.session_state[storage_key],
                column_config={"New IFRS Line": st.column_config.SelectboxColumn(options=target_options)},
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_widget_{i}" # Unique key prevents overwriting
            )
            
            # Update state immediately
            st.session_state[storage_key] = edited_alloc
            
            # Validation
            current_sum = edited_alloc[year_cols].sum()
            diffs = orig_vals - current_sum
            
            cols = st.columns(len(year_cols))
            for idx, y in enumerate(year_cols):
                if abs(diffs[y]) < 1: 
                    cols[idx].success(f"{y}: Balanced")
                else: 
                    cols[idx].error(f"{y} Remainder: {diffs[y]:,.0f}")
            
            # Prepare for final aggregation
            temp = edited_alloc.copy()
            temp["_source"] = src
            alloc_list.append(temp)

    st.divider()
    b1, b2 = st.columns([1, 1])
    if b1.button("← Back"): st.session_state.step = 3; st.rerun()
    if b2.button("Finalize & Generate →"):
        st.session_state.final_alloc = pd.concat(alloc_list) if alloc_list else pd.DataFrame()
        st.session_state.step = 5
        st.rerun()

def step_5_report():
    render_progress(5)
    st.subheader("Step 5: IFRS 18 Presentation")
    
    # Inputs
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    allocs = st.session_state.get("final_alloc", pd.DataFrame())
    year_cols = [c for c in df.columns if c != "line item"]
    template_key = st.session_state.template_key
    
    policies = {
        "cash_is_operating": st.session_state.get("policy_cash", "No"),
        "finance_is_operating": st.session_state.get("policy_finance", "No")
    }

    # Build Master
    g_lines, d_lines = get_ifrs18_data()
    all_lines = sorted(list(set(g_lines + d_lines)))
    
    final = pd.DataFrame({"line item": all_lines})
    final["Category"] = final["line item"].apply(lambda x: classify_category(x, template_key, policies))
    final = final.set_index("line item")
    for y in year_cols: final[y] = 0.0
    
    changes = []
    
    # 1. Standard Maps
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
            
            # Remainder handling
            rem = orig - allocated_sum
            if rem.abs().sum() > 1:
                 def_target = mapping[mapping["uploaded_line"]==src]["target_line"].values[0]
                 if def_target in final.index:
                     for y in year_cols: final.at[def_target, y] += rem[y]
                     changes.append({"Source": src, "Action": "Remainder", "Target": def_target, "Amount": rem[year_cols[0]]})

    # Final Display Prep
    final = final.reset_index()
    final = final[final[year_cols].abs().sum(axis=1) > 0.01] # Hide empty rows
    
    # Order by Category
    order = {"Operating": 1, "Investing": 2, "Financing": 3, "Income Tax": 4, "Discontinued Ops": 5}
    final["order"] = final["Category"].map(order).fillna(99)
    final = final.sort_values(["order", "line item"]).drop(columns=["order"])
    
    t1, t2 = st.tabs(["📄 Final Statement", "🔄 Changes Ledger"])
    
    with t1:
        st.dataframe(final.style.format({y: "{:,.0f}" for y in year_cols}), use_container_width=True, height=600)
        csv = final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel/CSV", csv, "IFRS18_PwC_Output.csv", "text/csv")
        
    with t2:
        st.dataframe(pd.DataFrame(changes), use_container_width=True)

    if st.button("Start New Conversion"):
        st.session_state.clear()
        st.rerun()

# --- Main Execution ---
def main():
    render_header()
    init_session_state()
    
    if st.session_state.step == 1: step_1_upload()
    elif st.session_state.step == 2: step_2_model()
    elif st.session_state.step == 3: step_3_map()
    elif st.session_state.step == 4: step_4_redistribute()
    elif st.session_state.step == 5: step_5_report()

if __name__ == "__main__":
    main()
