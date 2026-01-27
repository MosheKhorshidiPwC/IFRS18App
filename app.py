import io
import re
from typing import List, Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from rapidfuzz import process, fuzz
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="IFRS 18 Converter | PwC",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Professional Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
        color: #2D2D2D;
    }
    
    /* Header */
    h1, h2, h3 { font-weight: 700; color: #2D2D2D; }
    
    /* Buttons */
    .stButton > button {
        background-color: #D04A02; 
        color: white; 
        border-radius: 4px; 
        font-weight: 600;
        border: none;
        height: 3em;
        width: 100%;
        transition: 0.2s;
    }
    .stButton > button:hover {
        background-color: #b03d00;
        color: white;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f2f2f2;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Progress */
    .step-active { color: #D04A02; font-weight: bold; border-left: 4px solid #D04A02; padding-left: 10px; margin-bottom: 10px;}
    .step-inactive { color: #666; padding-left: 14px; margin-bottom: 10px;}
    
    /* Tables */
    .stDataFrame { border: 1px solid #ddd; border-radius: 5px; }
    
    /* Metric Box */
    div[data-testid="stMetricValue"] { font-size: 1.1rem; color: #D04A02; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Header ---
def render_header():
    c1, c2 = st.columns([0.6, 4])
    with c1:
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=120)
    with c2:
        st.markdown("## IFRS 18 Financial Statement Converter")
        st.caption("Automated classification, granular ungrouping, and professional reporting engine.")
    st.divider()

# --- 4. Data Engines ---

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
    possible = ["line item", "description", "account", "label", "caption"]
    line_col = next((c for c in df.columns if c.lower() in possible), df.columns[0])
    df = df.rename(columns={line_col: "line item"})
    valid_cols = ["line item"]
    for c in df.columns:
        if c == "line item": continue
        clean = str(c).replace(',', '').replace('.', '')
        if len(clean) == 4 and clean.isdigit():
            valid_cols.append(c)
            df[c] = df[c].apply(clean_financial_value)
    return df[valid_cols]

# --- 5. Template Definitions (Exact Match) ---

def get_template_structure(key):
    """
    Returns tuple: (List of Groups [G], List of Details)
    Based on the users strict requirement.
    """
    
    # Common Groups across most
    base_groups = [
        "Revenue from the sale of goods or services", 
        "Cost of sales , cost of goods", 
        "Sales and marketing", 
        "Research and development", 
        "General and administrative expenses", 
        "Other operating expenses"
    ]

    if key == "Investing Entity":
        groups = base_groups + ["Interest expense", "Income expense"]
        details = [
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency.",
            "Income or expense form Government grants related to operations",
            "FX differences on trade receivables/payables",
            "Impairment losses/reversals on trade receivables",
            "Rental income from investment property",
            "Fair value gains and losses from investment property ",
            "Dividends recieved from investment entities.",
            "Bank fees not related to a specefic borrowing",
            "Interest from investment debt securities",
            "Income and expenses from cash and cash equivalents",
            "Net gain / loss on investment entites at fair value",
            "Gain on disposal of investment entities / Investment property at fair value",
            "Realized FX gains/losses on investment entities / Investment property at fair value",
            "Impairment losses/reversals on investment entities / Investment property at fair value",
            "Net gain/loss on derivatives that hedge operating investments",
            "Gain or loss on lease modifications or remeasurements related to ROU",
            "Variable lease payments",
            "Depreciation of ROU",
            "Interest expense on lease liability",
            "Interest income from loans granted to third parties (non-customers)",
            "FX differences on financing debt",
            "Fair value changes on derivatives used solely to hedge financing debt ",
            "Fair value gains and losses on a liability designated at fair value through profit or loss",
            "Share of profit/loss from associates or joint ventures – equity method (IAS 28)",
            "Impairment losses on equity-accounted investments",
            "Net interest expense (income) on a net defined benefit liability (asset)",
            "FX on lease liabilities",
            "Dividends from associates measured at equity method",
            "Income tax expense (benefit)",
            "Discontinued operations"
        ]
        return groups, details

    elif key == "Financing Entity":
        groups = base_groups + ["Other Interest expense", "Other Income expense"]
        details = [
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency.",
            "Income or expense form Government grants related to operations",
            "Interest income on loans to customers",
            "Interest income on credit facilities to customers",
            "Interest income on bonds related to financing customers",
            "Interest expense on customer deposits",
            "FX differences on trade receivables/payables",
            "Impairment losses/reversals on trade receivables",
            "Income and expenses from cash and cash equivalents",
            "Interest on loans/bonds not related to customer financing",
            "FX on customer loans",
            "Loan origination fees",
            "Late customers payment penalties",
            "Expected credit losses from account receviables (AR) (IFRS 9)",
            "Net gain/loss on derivatives hedging customer loans",
            "Management fees for servicing customer loans ",
            "Gain or loss on lease modifications or remeasurements related to ROU",
            "Depreciation of ROU",
            "Variable lease payments",
            "Bank fees not related to a specefic borrowing",
            "FX differences on financing debt used to fund customer loans",
            "Rental income from investment property",
            "Fair value gains and losses from investment property ",
            "Dividends recieved from investment entities.",
            "Interest from investment debt securities",
            "Net gain / loss on investment entites at fair value",
            "Gain on disposal of investment entities / Investment property at fair value",
            "Realized FX gains/losses on investment entities / Investment property at fair value",
            "Impairment losses/reversals on investment entities / Investment property at fair value",
            "Net gain/loss on derivatives that hedge investment assets",
            "Interest expense on lease liability",
            "Interest income from loans granted to third parties (non-customers)",
            "FX differences on financing debt",
            "Fair value changes on derivatives used solely to hedge financing debt ",
            "Fair value gains and losses on a liability designated at fair value through profit or loss",
            "Share of profit/loss from associates or joint ventures – equity method (IAS 28)",
            "Impairment losses on equity-accounted investments",
            "Dividends from associates measured at equity method",
            "FX on lease liabilities",
            "Interest expenses on a contract liability with a significant financing component",
            "FX differences on loans received from third parties",
            "Interest expense arise from lease liabilities",
            "Net interest expense (income) on a net defined benefit liability (asset)",
            "Income tax expense (benefit)",
            "Discontinued operations"
        ]
        return groups, details

    else: # Other
        groups = base_groups + ["Interest expense", "Income expense"]
        details = [
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency.",
            "Income or expense form Government grants related to operations",
            "FX differences on trade receivables/payables",
            "Impairment losses/reversals on trade receivables",
            "Rental income from property used in operations/ Investment property",
            "Gain or loss on lease modifications or remeasurements related to ROU",
            "Depreciation of ROU",
            "Interest expense from lease liabilities",
            "Interest expenses on trade payables",
            "Variable lease payments",
            "Bank fees not related to a specefic borrowing",
            "Fair value gains and losses from investment property ",
            "Dividends recieved from investment entities.",
            "Interest from investment debt securities",
            "Net gain / loss on investment entites at fair value",
            "Gain on disposal of investment entities / Investment property at fair value",
            "Realized FX gains/losses on investment entities / Investment property at fair value",
            "Impairment losses/reversals on investment entities / Investment property at fair value",
            "Net gain/loss on derivatives that hedge investment assets",
            "Interest expense on lease liability",
            "Interest income from loans granted to third parties (non-customers)",
            "FX differences on financing debt",
            "Fair value changes on derivatives used solely to hedge financing debt ",
            "Fair value gains and losses on a liability designated at fair value through profit or loss",
            "Share of profit/loss from associates or joint ventures – equity method (IAS 28)",
            "Impairment losses on equity-accounted investments",
            "Dividends from associates measured at equity method",
            "Income and expenses from cash and cash equivalents",
            "FX on lease liabilities",
            "Interest expense on loans received from third party ",
            "FX differences on loans received from third parties",
            "Net interest expense (income) on a net defined benefit liability (asset)",
            "Interest expenses on a contract liability with a significant financing component",
            "Income tax expense (benefit)",
            "Discontinued operations"
        ]
        return groups, details

def get_category_for_line(line, key, policies):
    l = line.lower()
    # Policies (Financing Entity specific)
    if key == "Financing Entity":
        if "cash and cash equivalents" in l: return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
        if "not related to customer financing" in l: return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
    
    # Universal
    if "income tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    
    # Simple Keyword Logic
    if "interest expense" in l or "financing debt" in l or "lease liability" in l or "lease liabilities" in l: return "Financing"
    if "investing" in l or "investment" in l or "dividends" in l or "equity method" in l: return "Investing"
    
    # Overrides based on Template Key
    if key == "Investing Entity" and "investment" in l: return "Operating"
    if key == "Financing Entity" and "customer" in l: return "Operating"
    
    return "Operating" # Default

# --- 6. State ---
if "step" not in st.session_state: st.session_state.step = 1
if "template_key" not in st.session_state: st.session_state.template_key = "Other main buisness activities"
if "p_cash" not in st.session_state: st.session_state.p_cash = "No"
if "p_fin" not in st.session_state: st.session_state.p_fin = "No"

# --- 7. UI Steps ---

def render_sidebar():
    with st.sidebar:
        st.markdown("### Process Status")
        steps = ["Upload", "Model Selection", "Classify Groups", "Granular Breakdown", "Final Report"]
        for i, s in enumerate(steps, 1):
            cls = "step-active" if st.session_state.step == i else "step-inactive"
            st.markdown(f"<div class='{cls}'>{i}. {s}</div>", unsafe_allow_html=True)
        st.divider()
        st.info("Selection state is persistent.")

def step_1_upload():
    st.subheader("1. Upload Financial Data")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        f = st.file_uploader("Upload Excel or CSV", type=['xlsx', 'csv'])
        if f:
            df = load_data_file(f)
            if not df.empty:
                st.session_state.uploaded_df = df
                st.toast("File Uploaded!", icon="✅")
    with c2:
        if "uploaded_df" in st.session_state:
            st.dataframe(st.session_state.uploaded_df.head(5), use_container_width=True, height=200)
            if st.button("Next: Business Model →"): st.session_state.step = 2; st.rerun()

def step_2_model():
    st.subheader("2. Business Model & Policies")
    q1 = st.radio("Does the entity invest in financial assets as a main activity?", ["No", "Yes"], index=0, key="rad_q1")
    q2 = st.radio("Does the entity provide financing to customers as a main activity?", ["No", "Yes"], index=0, key="rad_q2")
    
    if q1 == "Yes": temp = "Investing Entity"
    elif q2 == "Yes": temp = "Financing Entity"
    else: temp = "Other main buisness activities"
    st.session_state.template_key = temp
    
    if temp == "Financing Entity":
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            p1 = st.radio("Classify Cash & Equivalents as Operating?", ["Yes", "No"], key="rad_p1")
            st.session_state.p_cash = p1
        with c2:
            p2 = st.radio("Classify Non-Customer Financing Interest as Operating?", ["Yes", "No"], index=1, key="rad_p2")
            st.session_state.p_fin = p2
    
    st.success(f"Template: **{temp}**")
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 1; st.rerun()
    if b2.button("Confirm & Continue →"): st.session_state.step = 3; st.rerun()

def step_3_map_groups():
    st.subheader("3. Classify to IFRS 18 Groups")
    st.write("Map your source lines to the high-level **Group Buckets** first.")
    
    df = st.session_state.uploaded_df
    # Get just the groups
    groups, _ = get_template_structure(st.session_state.template_key)
    
    # Add a visual indicator
    group_options = [f"[G] {g}" for g in groups]
    
    if "group_map_df" not in st.session_state:
        m = []
        for line in df["line item"]:
            # Default mapping logic (dumb) or fuzzy
            best, _, _ = process.extractOne(str(line), group_options, scorer=fuzz.token_sort_ratio)
            m.append({"uploaded_line": line, "Mapped Group": best})
        st.session_state.group_map_df = pd.DataFrame(m)

    edited = st.data_editor(
        st.session_state.group_map_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "Mapped Group": st.column_config.SelectboxColumn("Target Group Bucket", options=group_options, width="large")
        },
        use_container_width=True, hide_index=True, height=500, key="editor_step3"
    )
    st.session_state.group_map_df = edited
    
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 2; st.rerun()
    if b2.button("Proceed to Breakdown →"): st.session_state.step = 4; st.rerun()

def step_4_breakdown():
    st.subheader("4. Granular Breakdown")
    st.info("Select detailed IFRS 18 lines and allocate amounts from your Groups.")
    
    df = st.session_state.uploaded_df
    groups_list, details_list = get_template_structure(st.session_state.template_key)
    year_cols = [c for c in df.columns if c != "line item"]
    
    # Groups available to pull from
    avail_groups = [f"[G] {g}" for g in groups_list]
    
    # We need a dynamic list of allocations.
    # We will use a session state dataframe to hold the allocations the user creates.
    if "allocations_table" not in st.session_state:
        # Columns: Target Detail Line | Source Group | Amount Y1 | Amount Y2...
        cols = ["Detailed IFRS Line", "Source Group"] + year_cols
        st.session_state.allocations_table = pd.DataFrame(columns=cols)

    # UI: Add new allocation
    st.markdown("**Add Allocation Rule**")
    
    # Main Editor
    edited_allocs = st.data_editor(
        st.session_state.allocations_table,
        column_config={
            "Detailed IFRS Line": st.column_config.SelectboxColumn(options=details_list, required=True, width="medium"),
            "Source Group": st.column_config.SelectboxColumn(options=avail_groups, required=True, width="medium"),
            **{y: st.column_config.NumberColumn(format="%.0f") for y in year_cols}
        },
        num_rows="dynamic",
        use_container_width=True,
        key="alloc_editor_main"
    )
    st.session_state.allocations_table = edited_allocs
    
    st.markdown("---")
    
    # Calculate Remainders in Groups
    st.markdown("##### Group Balance Check")
    
    # 1. Sum up originals per mapped group
    group_map = st.session_state.group_map_df
    group_totals = {g: {y: 0.0 for y in year_cols} for g in avail_groups}
    
    for _, row in group_map.iterrows():
        g = row["Mapped Group"]
        src_line = row["uploaded_line"]
        src_vals = df[df["line item"] == src_line].iloc[0][year_cols]
        for y in year_cols:
            group_totals[g][y] += src_vals[y]
            
    # 2. Subtract Allocations
    for _, row in edited_allocs.iterrows():
        g = row["Source Group"]
        if g in group_totals:
            for y in year_cols:
                val = row[y] if pd.notnull(row[y]) else 0.0
                group_totals[g][y] -= float(val)
    
    # Display Balances
    balance_df = pd.DataFrame.from_dict(group_totals, orient='index').reset_index().rename(columns={"index": "Group"})
    # Filter out empty groups for cleanliness
    balance_df["Total"] = balance_df[year_cols].sum(axis=1)
    balance_df = balance_df[balance_df["Total"].abs() > 0.1].drop(columns=["Total"])
    
    st.dataframe(balance_df.style.format({y: "{:,.0f}" for y in year_cols}), use_container_width=True)

    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 3; st.rerun()
    if b2.button("Generate Final Report →"): st.session_state.step = 5; st.rerun()

def step_5_report():
    st.subheader("5. IFRS 18 Consolidated Statement")
    
    # Gather Inputs
    df = st.session_state.uploaded_df
    group_map = st.session_state.group_map_df
    allocs = st.session_state.allocations_table
    year_cols = [c for c in df.columns if c != "line item"]
    
    key = st.session_state.template_key
    policies = {"cash_op": st.session_state.p_cash, "fin_op": st.session_state.p_fin}
    
    # Get Master List (Groups + Details)
    g_list, d_list = get_template_structure(key)
    
    # Build Result DF
    # We want Rows for Groups AND Rows for Details
    # Groups usually aggregate what's left. Details aggregate what's allocated.
    
    final_data = {} # Key: Line Item Name, Value: Series of amounts
    
    # Initialize all potential lines
    all_lines = [f"[G] {g}" for g in g_list] + d_list
    for l in all_lines:
        final_data[l] = pd.Series(0.0, index=year_cols)
        
    # 1. Pour Source Data into Groups
    for _, row in group_map.iterrows():
        target_g = row["Mapped Group"]
        src_line = row["uploaded_line"]
        vals = df[df["line item"] == src_line].iloc[0][year_cols]
        
        # Add to Group
        if target_g in final_data:
            for y in year_cols: final_data[target_g][y] += vals[y]
            
    # 2. Move Allocations (Subtract from Group, Add to Detail)
    for _, row in allocs.iterrows():
        src_g = row["Source Group"]
        target_d = row["Detailed IFRS Line"]
        
        for y in year_cols:
            val = float(row[y]) if pd.notnull(row[y]) else 0.0
            
            # Subtract from Group
            if src_g in final_data:
                final_data[src_g][y] -= val
                
            # Add to Detail
            if target_d in final_data:
                final_data[target_d][y] += val
                
    # 3. Convert to DataFrame
    final_df = pd.DataFrame.from_dict(final_data, orient='index')
    final_df.index.name = "Line Item"
    final_df = final_df.reset_index()
    
    # Clean names (remove [G]) for display? Maybe keep to distinguish.
    # Classify Categories
    final_df["Category"] = final_df["Line Item"].apply(lambda x: classify_category(x.replace("[G] ", ""), key, policies))
    
    # 4. Filter Zero Rows
    final_df = final_df[final_df[year_cols].abs().sum(axis=1) > 0.1]
    
    # 5. Format Output (Subtotals)
    pl_rows = []
    def get_tot(cat): return final_df[final_df["Category"] == cat][year_cols].sum()
    
    # Operating
    pl_rows.append({"Line Item": "<b>OPERATING CATEGORY</b>", "Header": True})
    op_subset = final_df[final_df["Category"] == "Operating"]
    for idx, r in op_subset.iterrows():
        d = {"Line Item": r["Line Item"].replace("[G] ", "")}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    
    op_tot = get_tot("Operating")
    d_op = {"Line Item": "<b>Operating Profit or Loss</b>", "Total": True}; d_op.update(op_tot.to_dict())
    pl_rows.append(d_op)
    
    # Investing
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>INVESTING CATEGORY</b>", "Header": True})
    inv_subset = final_df[final_df["Category"] == "Investing"]
    for idx, r in inv_subset.iterrows():
        d = {"Line Item": r["Line Item"].replace("[G] ", "")}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
        
    inv_tot = get_tot("Investing")
    ebit_tot = op_tot + inv_tot
    d_ebit = {"Line Item": "<b>Profit Before Financing & Tax</b>", "Total": True}; d_ebit.update(ebit_tot.to_dict())
    pl_rows.append(d_ebit)
    
    # Financing
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>FINANCING CATEGORY</b>", "Header": True})
    fin_subset = final_df[final_df["Category"] == "Financing"]
    for idx, r in fin_subset.iterrows():
        d = {"Line Item": r["Line Item"].replace("[G] ", "")}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
        
    fin_tot = get_tot("Financing")
    pbt_tot = ebit_tot + fin_tot
    d_pbt = {"Line Item": "<b>Profit Before Tax</b>", "Total": True}; d_pbt.update(pbt_tot.to_dict())
    pl_rows.append(d_pbt)
    
    # Others
    tax_tot = get_tot("Income Tax")
    if tax_tot.abs().sum() > 0:
        d = {"Line Item": "Income tax expense"}; d.update(tax_tot.to_dict())
        pl_rows.append(d)
    
    disc_tot = get_tot("Discontinued Ops")
    if disc_tot.abs().sum() > 0:
        d = {"Line Item": "Discontinued operations"}; d.update(disc_tot.to_dict())
        pl_rows.append(d)
        
    net_tot = pbt_tot + tax_tot + disc_tot
    pl_rows.append({"Line Item": " "})
    d_net = {"Line Item": "<b>PROFIT OR LOSS</b>", "Total": True, "Grand": True}; d_net.update(net_tot.to_dict())
    pl_rows.append(d_net)
    
    # Render
    display = pd.DataFrame(pl_rows)
    
    def fmt(v): 
        if pd.isna(v) or isinstance(v, str): return v
        if v == 0: return "-"
        s = "{:,.0f}".format(abs(v))
        return f"({s})" if v < 0 else s
    
    def style_row(row):
        if row.get("Header"): return ['background-color: #f4f4f4; font-weight: bold; border-bottom: 2px solid #333; color: #D04A02'] * len(row)
        if row.get("Grand"): return ['background-color: #e6f2ff; font-weight: bold; border-top: 2px solid #333; border-bottom: 4px double #333'] * len(row)
        if row.get("Total"): return ['font-weight: bold; border-top: 1px solid #333; background-color: white'] * len(row)
        return ['background-color: white'] * len(row)

    st.write(
        display.style.apply(style_row, axis=1)
        .format({y: fmt for y in year_cols})
        .hide(axis="index").hide(subset=["Header", "Total", "Grand"], axis="columns").to_html(),
        unsafe_allow_html=True
    )
    
    # CSV
    view = display.drop(columns=["Header", "Total", "Grand"], errors="ignore")
    st.download_button("📥 Download Report", view.to_csv(index=False).encode('utf-8'), "IFRS18.csv", "text/csv")
    
    if st.button("Start New Project"):
        st.session_state.clear()
        st.rerun()

# --- 8. Classification Logic (Categorization for Report) ---
def classify_category(line, key, policies):
    l = line.lower()
    if "income tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    
    # Policy Checks
    if key == "Financing Entity":
        if "cash" in l and "equivalents" in l: return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
        if "not related to customer financing" in l: return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
        if "customer" in l or "loans" in l: return "Operating" # Financing entity core biz
    
    if "interest expense" in l or "financing debt" in l: return "Financing"
    if "invest" in l or "dividends" in l or "associates" in l: return "Investing"
    
    return "Operating"

# --- Main ---
def main():
    render_header()
    render_sidebar()
    if st.session_state.step == 1: step_1_upload()
    elif st.session_state.step == 2: step_2_model()
    elif st.session_state.step == 3: step_3_map_groups()
    elif st.session_state.step == 4: step_4_breakdown()
    elif st.session_state.step == 5: step_5_report()

if __name__ == "__main__":
    main()
