import io
import re
from typing import List, Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    .stButton > button {
        background-color: #D04A02; 
        color: white; 
        border-radius: 4px; 
        font-weight: 600;
        border: none;
        height: 3em;
        width: 100%;
    }
    .stButton > button:hover { background-color: #b03d00; color: white; }
    
    /* Tables */
    .stDataFrame { border: 1px solid #ddd; border-radius: 5px; }
    
    /* Sidebar Steps */
    .step-active { color: #D04A02; font-weight: bold; border-left: 4px solid #D04A02; padding-left: 10px; margin-bottom: 10px;}
    .step-inactive { color: #666; padding-left: 14px; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- 3. Header ---
def render_header():
    c1, c2 = st.columns([0.6, 4])
    with c1:
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=120)
    with c2:
        st.markdown("## IFRS 18 Financial Statement Converter")
        st.caption("Manual classification to Groups, followed by granular Breakdown.")
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

# --- 5. THE TEMPLATE DEFINITIONS (Separating Groups vs Details) ---

def get_template_data(template_name):
    """
    Returns a DataFrame with columns: ['Line Item', 'Type', 'Category']
    Type is either 'Group' (for initial mapping) or 'Detail' (for breakdown).
    """
    
    rows = []
    def add(name, type_, cat):
        rows.append({"Line Item": name, "Type": type_, "Category": cat})

    # --- SHARED GROUPS (Common across most templates) ---
    common_groups = [
        ("Revenue from the sale of goods or services", "Operating"),
        ("Cost of sales, cost of goods", "Operating"),
        ("Sales and marketing", "Operating"),
        ("Research and development", "Operating"),
        ("General and administrative expenses", "Operating"),
        ("Other operating expenses", "Operating")
    ]

    # --- TEMPLATE 1: INVESTING ENTITY ---
    if template_name == "Investing Entity":
        # Groups
        for n, c in common_groups: add(n, "Group", c)
        add("Interest expense", "Group", "Financing")
        add("Income expense", "Group", "Financing")
        
        # Details
        details = [
            ("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            ("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            ("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            ("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            ("Income or expense form Government grants related to operations", "Operating"),
            ("FX differences on trade receivables/payables", "Operating"),
            ("Impairment losses/reversals on trade receivables", "Operating"),
            ("Rental income from investment property", "Operating"),
            ("Fair value gains and losses from investment property", "Operating"),
            ("Dividends recieved from investment entities", "Operating"),
            ("Bank fees not related to a specefic borrowing", "Operating"),
            ("Interest from investment debt securities", "Operating"),
            ("Income and expenses from cash and cash equivalents", "Operating"),
            ("Net gain / loss on investment entites at fair value", "Operating"),
            ("Gain on disposal of investment entities / Investment property at fair value", "Operating"),
            ("Realized FX gains/losses on investment entities / Investment property at fair value", "Operating"),
            ("Impairment losses/reversals on investment entities / Investment property at fair value", "Operating"),
            ("Net gain/loss on derivatives that hedge operating investments", "Operating"),
            ("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            ("Variable lease payments", "Operating"),
            ("Depreciation of ROU", "Operating"),
            ("Interest expense on lease liability", "Financing"),
            ("Interest income from loans granted to third parties (non-customers)", "Investing"),
            ("FX differences on financing debt", "Financing"),
            ("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            ("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            ("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            ("Impairment losses on equity-accounted investments", "Investing"),
            ("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            ("FX on lease liabilities", "Financing"),
            ("Dividends from associates measured at equity method", "Investing"),
            ("Income tax expense (benefit)", "Income Tax"),
            ("Discontinued operations", "Discontinued Ops")
        ]
        for n, c in details: add(n, "Detail", c)

    # --- TEMPLATE 2: FINANCING ENTITY ---
    elif template_name == "Financing Entity":
        # Groups
        for n, c in common_groups: add(n, "Group", c)
        add("Other Interest expense", "Group", "Financing")
        add("Other Income expense", "Group", "Financing")

        # Details
        details = [
            ("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            ("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            ("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            ("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            ("Income or expense form Government grants related to operations", "Operating"),
            ("Interest income on loans to customers", "Operating"),
            ("Interest income on credit facilities to customers", "Operating"),
            ("Interest income on bonds related to financing customers", "Operating"),
            ("Interest expense on customer deposits", "Operating"),
            ("FX differences on trade receivables/payables", "Operating"),
            ("Impairment losses/reversals on trade receivables", "Operating"),
            # Policy Dependent
            ("Income and expenses from cash and cash equivalents", "Accounting Policy"),
            ("Interest on loans/bonds not related to customer financing", "Accounting Policy"),
            ("FX on customer loans", "Operating"),
            ("Loan origination fees", "Operating"),
            ("Late customers payment penalties", "Operating"),
            ("Expected credit losses from account receviables (AR) (IFRS 9)", "Operating"),
            ("Net gain/loss on derivatives hedging customer loans", "Operating"),
            ("Management fees for servicing customer loans", "Operating"),
            ("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            ("Depreciation of ROU", "Operating"),
            ("Variable lease payments", "Operating"),
            ("Bank fees not related to a specefic borrowing", "Operating"),
            ("FX differences on financing debt used to fund customer loans", "Operating"),
            ("Rental income from investment property", "Investing"),
            ("Fair value gains and losses from investment property", "Investing"),
            ("Dividends recieved from investment entities", "Investing"),
            ("Interest from investment debt securities", "Investing"),
            ("Net gain / loss on investment entites at fair value", "Investing"),
            ("Gain on disposal of investment entities / Investment property at fair value", "Investing"),
            ("Realized FX gains/losses on investment entities / Investment property at fair value", "Investing"),
            ("Impairment losses/reversals on investment entities / Investment property at fair value", "Investing"),
            ("Net gain/loss on derivatives that hedge investment assets", "Investing"),
            ("Interest expense on lease liability", "Financing"),
            ("Interest income from loans granted to third parties (non-customers)", "Investing"),
            ("FX differences on financing debt", "Financing"),
            ("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            ("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            ("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            ("Impairment losses on equity-accounted investments", "Investing"),
            ("Dividends from associates measured at equity method", "Investing"),
            ("FX on lease liabilities", "Financing"),
            ("Interest expenses on a contract liability with a significant financing component", "Financing"),
            ("FX differences on loans received from third parties", "Financing"),
            ("Interest expense arise from lease liabilities", "Financing"),
            ("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            ("Income tax expense (benefit)", "Income Tax"),
            ("Discontinued operations", "Discontinued Ops")
        ]
        for n, c in details: add(n, "Detail", c)

    # --- TEMPLATE 3: OTHER / GENERAL ---
    else:
        # Groups
        for n, c in common_groups: add(n, "Group", c)
        add("Interest expense", "Group", "Financing")
        add("Income expense", "Group", "Financing")

        # Details
        details = [
            ("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            ("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            ("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            ("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            ("Income or expense form Government grants related to operations", "Operating"),
            ("FX differences on trade receivables/payables", "Operating"),
            ("Impairment losses/reversals on trade receivables", "Operating"),
            ("Rental income from property used in operations/ Investment property", "Investing"),
            ("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            ("Depreciation of ROU", "Operating"),
            ("Interest expense from lease liabilities", "Financing"),
            ("Interest expenses on trade payables", "Operating"),
            ("Variable lease payments", "Operating"),
            ("Bank fees not related to a specefic borrowing", "Operating"),
            ("Fair value gains and losses from investment property", "Investing"),
            ("Dividends recieved from investment entities", "Investing"),
            ("Interest from investment debt securities", "Investing"),
            ("Net gain / loss on investment entites at fair value", "Investing"),
            ("Gain on disposal of investment entities / Investment property at fair value", "Investing"),
            ("Realized FX gains/losses on investment entities / Investment property at fair value", "Investing"),
            ("Impairment losses/reversals on investment entities / Investment property at fair value", "Investing"),
            ("Net gain/loss on derivatives that hedge investment assets", "Investing"),
            ("Interest expense on lease liability", "Financing"),
            ("Interest income from loans granted to third parties (non-customers)", "Investing"),
            ("FX differences on financing debt", "Financing"),
            ("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            ("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            ("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            ("Impairment losses on equity-accounted investments", "Investing"),
            ("Dividends from associates measured at equity method", "Investing"),
            ("Income and expenses from cash and cash equivalents", "Investing"),
            ("FX on lease liabilities", "Financing"),
            ("Interest expense on loans received from third party", "Financing"),
            ("FX differences on loans received from third parties", "Financing"),
            ("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            ("Interest expenses on a contract liability with a significant financing component", "Financing"),
            ("Income tax expense (benefit)", "Income Tax"),
            ("Discontinued operations", "Discontinued Ops")
        ]
        for n, c in details: add(n, "Detail", c)

    return pd.DataFrame(rows)

def resolve_policy_category(cat, row_name, policies):
    """Dynamic policy resolver."""
    if cat != "Accounting Policy":
        return cat
    
    name = row_name.lower()
    if "cash" in name and "equivalents" in name:
        return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
    if "loans/bonds not related" in name:
        return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
    return "Operating"

# --- 6. State Management ---
if "step" not in st.session_state: st.session_state.step = 1
if "template_key" not in st.session_state: st.session_state.template_key = "Other main buisness activities"
if "p_cash" not in st.session_state: st.session_state.p_cash = "No"
if "p_fin" not in st.session_state: st.session_state.p_fin = "No"

# --- 7. UI Components ---

def render_sidebar():
    with st.sidebar:
        st.markdown("### Process Status")
        steps = ["Upload", "Model Selection", "Map Groups", "Breakdown", "Final Report"]
        for i, s in enumerate(steps, 1):
            cls = "step-active" if st.session_state.step == i else "step-inactive"
            st.markdown(f"<div class='{cls}'>{i}. {s}</div>", unsafe_allow_html=True)
        st.divider()
        st.info("💡 **Selection Saved:** Data persists automatically.")

def step_1_upload():
    st.subheader("1. Upload Financial Data")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        f = st.file_uploader("Upload Excel or CSV", type=['xlsx', 'csv'])
        if f:
            df = load_data_file(f)
            if not df.empty and len(df.columns) > 1:
                st.session_state.uploaded_df = df
                st.toast("File Uploaded!", icon="✅")
    with c2:
        if "uploaded_df" in st.session_state:
            st.dataframe(st.session_state.uploaded_df.head(5), use_container_width=True, height=200)
            if st.button("Next: Business Model →"):
                st.session_state.step = 2
                st.rerun()

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
        st.markdown("##### Accounting Policy Choices")
        c1, c2 = st.columns(2)
        with c1:
            p1 = st.radio("Classify Cash & Equivalents as Operating?", ["Yes", "No"], key="rad_p1")
            st.session_state.p_cash = p1
        with c2:
            p2 = st.radio("Classify Non-Customer Financing Interest as Operating?", ["Yes", "No"], index=1, key="rad_p2")
            st.session_state.p_fin = p2
    
    st.info(f"Applying Template: **{temp}**")
    
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 1; st.rerun()
    if b2.button("Confirm & Map Groups →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    st.subheader("3. Map Line Items to Groups")
    st.write("Assign each uploaded line to an **IFRS 18 Group**.")
    
    df = st.session_state.uploaded_df
    ref_df = get_template_data(st.session_state.template_key)
    
    # Filter for GROUPS only
    group_options = sorted(ref_df[ref_df["Type"] == "Group"]["Line Item"].unique().tolist())
    
    # Initialize Mapping Table (No Fuzzy matching, purely manual selection)
    if "mapping_df" not in st.session_state:
        m = []
        for line in df["line item"]:
            # Default to first group or empty
            m.append({"uploaded_line": line, "IFRS 18 Group": group_options[0], "Breakdown?": "No"})
        st.session_state.mapping_df = pd.DataFrame(m)

    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "IFRS 18 Group": st.column_config.SelectboxColumn("Map to Group", options=group_options, width="large"),
            "Breakdown?": st.column_config.SelectboxColumn("Breakdown Required?", options=["No", "Yes"], width="small", help="Select Yes if you need to allocate parts of this amount to specific Detailed lines.")
        },
        use_container_width=True, hide_index=True, height=500, key="editor_map"
    )
    st.session_state.mapping_df = edited
    
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 2; st.rerun()
    
    has_breakdown = any(edited["Breakdown?"] == "Yes")
    lbl = "Proceed to Breakdown →" if has_breakdown else "Generate Report →"
    if b2.button(lbl):
        st.session_state.step = 4 if has_breakdown else 5
        st.rerun()

def step_4_redistribute():
    st.subheader("4. Granular Breakdown")
    st.info("Allocate amounts from the Groups into specific Detailed Line Items.")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    year_cols = [c for c in df.columns if c != "line item"]
    
    # Get DETAILED lines for dropdowns
    ref_df = get_template_data(st.session_state.template_key)
    detail_options = sorted(ref_df[ref_df["Type"] == "Detail"]["Line Item"].unique().tolist())
    
    breakdown_rows = mapping[mapping["Breakdown?"] == "Yes"]
    if breakdown_rows.empty: st.session_state.step = 5; st.rerun()
    
    alloc_list = []
    tabs = st.tabs([f"📝 {r['uploaded_line']}" for _, r in breakdown_rows.iterrows()])
    
    for i, tab in enumerate(tabs):
        with tab:
            row = breakdown_rows.iloc[i]
            src = row['uploaded_line']
            mapped_group = row['IFRS 18 Group']
            orig_vals = df[df["line item"] == src].iloc[0][year_cols]
            
            c1, c2 = st.columns([1, 3])
            c1.markdown(f"**Source:** `{src}`")
            c1.markdown(f"**Mapped Group:** `{mapped_group}`")
            c1.markdown("---")
            for y in year_cols: c1.metric(y, f"{orig_vals[y]:,.0f}")
            
            key = f"alloc_{src}_{i}"
            if key not in st.session_state:
                # Default empty alloc
                st.session_state[key] = pd.DataFrame([{"Detailed IFRS Line": detail_options[0], **{y: 0.0 for y in year_cols}}])
            
            with c2:
                edited = st.data_editor(
                    st.session_state[key],
                    column_config={"Detailed IFRS Line": st.column_config.SelectboxColumn(options=detail_options, width="large")},
                    num_rows="dynamic", use_container_width=True, key=f"wid_{key}"
                )
                st.session_state[key] = edited
                
                # Logic: Total Source - Allocated = Remaining in Group
                allocated_sum = edited[year_cols].sum()
                remaining_in_group = orig_vals - allocated_sum
                
                st.caption("Remaining amount stays in the mapped Group:")
                cols = st.columns(len(year_cols))
                for idx, y in enumerate(year_cols):
                    cols[idx].metric(y, f"{remaining_in_group[y]:,.0f}")
            
            temp = edited.copy()
            temp["_source"] = src
            alloc_list.append(temp)

    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 3; st.rerun()
    if b2.button("Generate Report →"):
        st.session_state.final_alloc = pd.concat(alloc_list) if alloc_list else pd.DataFrame()
        st.session_state.step = 5
        st.rerun()

def step_5_report():
    st.subheader("5. Consolidated Statement of Profit or Loss")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    allocs = st.session_state.get("final_alloc", pd.DataFrame())
    year_cols = [c for c in df.columns if c != "line item"]
    
    key = st.session_state.template_key
    policies = {"cash_op": st.session_state.p_cash, "fin_op": st.session_state.p_fin}
    
    # 1. Prepare Structure
    ref_df = get_template_data(key)
    # Unique lines
    final_lines = ref_df["Line Item"].unique()
    final = pd.DataFrame(index=final_lines)
    
    # Resolve Categories
    cat_map = {}
    for _, r in ref_df.iterrows():
        cat_map[r["Line Item"]] = resolve_policy_category(r["Category"], r["Line Item"], policies)
    
    final["Category"] = final.index.map(cat_map)
    for y in year_cols: final[y] = 0.0
    
    sankey_data = []

    # 2. Calculation
    # Iterate over original lines
    for _, m in mapping.iterrows():
        src = m["uploaded_line"]
        group_target = m["IFRS 18 Group"]
        
        # Get original values
        orig_vals = df[df["line item"] == src].iloc[0][year_cols]
        
        # Check for allocations
        allocated_amt = pd.Series(0.0, index=year_cols)
        
        if not allocs.empty:
            # Filter allocs for this source line
            src_allocs = allocs[allocs["_source"] == src]
            for _, r in src_allocs.iterrows():
                detail_target = r["Detailed IFRS Line"]
                # Add to Detail Line
                if detail_target in final.index:
                    for y in year_cols: final.at[detail_target, y] += r[y]
                    # Log flow
                    if r[year_cols[0]] != 0:
                        sankey_data.append({"Source": src, "Target": final.loc[detail_target, "Category"], "Value": abs(r[year_cols[0]])})
                
                allocated_amt += r[year_cols]

        # Remaining goes to Group
        remaining = orig_vals - allocated_amt
        if group_target in final.index:
            for y in year_cols: final.at[group_target, y] += remaining[y]
            if remaining[year_cols[0]] != 0:
                sankey_data.append({"Source": src, "Target": final.loc[group_target, "Category"], "Value": abs(remaining[year_cols[0]])})

    # 3. Format Output (Subtotals)
    def get_tot(cat): return final[final["Category"] == cat][year_cols].sum()
    pl_rows = []
    
    # Operating
    pl_rows.append({"Line Item": "<b>OPERATING CATEGORY</b>", "Header": True})
    op_df = final[final["Category"] == "Operating"]
    op_df = op_df[op_df[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in op_df.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    op_tot = get_tot("Operating")
    d_op = {"Line Item": "<b>Operating Profit or Loss</b>", "Total": True}; d_op.update(op_tot.to_dict())
    pl_rows.append(d_op)
    
    # Investing
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>INVESTING CATEGORY</b>", "Header": True})
    inv_df = final[final["Category"] == "Investing"]
    inv_df = inv_df[inv_df[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in inv_df.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    inv_tot = get_tot("Investing")
    ebit_tot = op_tot + inv_tot
    d_ebit = {"Line Item": "<b>Profit Before Financing & Tax</b>", "Total": True}; d_ebit.update(ebit_tot.to_dict())
    pl_rows.append(d_ebit)
    
    # Financing
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>FINANCING CATEGORY</b>", "Header": True})
    fin_df = final[final["Category"] == "Financing"]
    fin_df = fin_df[fin_df[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in fin_df.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    fin_tot = get_tot("Financing")
    pbt_tot = ebit_tot + fin_tot
    d_pbt = {"Line Item": "<b>Profit Before Tax</b>", "Total": True}; d_pbt.update(pbt_tot.to_dict())
    pl_rows.append(d_pbt)
    
    # Tax/Disc
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

    t1, t2 = st.tabs(["📄 Financial Statement", "📊 Flow Analysis"])
    with t1:
        st.write(
            display.style.apply(style_row, axis=1)
            .format({y: fmt for y in year_cols})
            .hide(axis="index").hide(subset=["Header", "Total", "Grand"], axis="columns").to_html(),
            unsafe_allow_html=True
        )
        view = display.drop(columns=["Header", "Total", "Grand"], errors="ignore")
        for y in year_cols: view[y] = view[y].apply(fmt)
        st.download_button("📥 Download Report", view.to_csv(index=False).encode('utf-8'), "IFRS18.csv", "text/csv")

    with t2:
        if sankey_data:
            sdf = pd.DataFrame(sankey_data).groupby(["Source", "Target"]).sum().reset_index()
            lbls = list(pd.concat([sdf["Source"], sdf["Target"]]).unique())
            imap = {l: i for i, l in enumerate(lbls)}
            fig = go.Figure(data=[go.Sankey(
                node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=lbls, color="#D04A02"),
                link=dict(source=sdf["Source"].map(imap), target=sdf["Target"].map(imap), value=sdf["Value"])
            )])
            fig.update_layout(title="Data Classification Flow")
            st.plotly_chart(fig, use_container_width=True)

    if st.button("Start New Project"):
        st.session_state.clear()
        st.rerun()

# --- Main ---
def main():
    render_header()
    render_sidebar()
    if st.session_state.step == 1: step_1_upload()
    elif st.session_state.step == 2: step_2_model()
    elif st.session_state.step == 3: step_3_map()
    elif st.session_state.step == 4: step_4_redistribute()
    elif st.session_state.step == 5: step_5_report()

if __name__ == "__main__":
    main()
