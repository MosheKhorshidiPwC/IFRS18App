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

# --- 2. Professional Styling (PwC Theme) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
        color: #2D2D2D;
    }
    
    /* Headers */
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
    </style>
""", unsafe_allow_html=True)

# --- 3. Logic Engines ---

def render_header():
    c1, c2 = st.columns([0.6, 4])
    with c1:
        # Placeholder for logo
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=120)
    with c2:
        st.markdown("## IFRS 18 Financial Statement Converter")
        st.caption("Automated classification, granular ungrouping, and professional reporting engine.")
    st.divider()

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

# --- 4. THE DATA KERNEL (Templates) ---

def get_template_data(template_name):
    """
    Returns a DataFrame containing the exact line items, categories, and Group flags (G).
    """
    
    # Helper to build rows
    def row(name, cat, is_group=False):
        prefix = "[G] " if is_group else ""
        return {"Line Item": name, "Display Name": f"{prefix}{name}", "Default Category": cat, "Is Group": is_group}

    data = []

    # --- TEMPLATE 1: INVESTING ENTITY ---
    if template_name == "Investing Entity":
        data = [
            row("Revenue from the sale of goods or services", "Operating"),
            row("Cost of sales, cost of goods", "Operating", True),
            row("Sales and marketing", "Operating", True),
            row("Research and development", "Operating", True),
            row("General and administrative expenses", "Operating", True),
            row("Other operating expenses", "Operating", True),
            row("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            row("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            row("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            row("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            row("Income or expense form Government grants related to operations", "Operating"),
            row("FX differences on trade receivables/payables", "Operating"),
            row("Impairment losses/reversals on trade receivables", "Operating"),
            row("Rental income from investment property", "Operating"),
            row("Fair value gains and losses from investment property", "Operating"),
            row("Dividends recieved from investment entities", "Operating"),
            row("Bank fees not related to a specefic borrowing", "Operating"),
            row("Interest from investment debt securities", "Operating"),
            row("Income and expenses from cash and cash equivalents", "Operating"),
            row("Net gain / loss on investment entites at fair value", "Operating"),
            row("Gain on disposal of investment entities / Investment property at fair value", "Operating"),
            row("Realized FX gains/losses on investment entities / Investment property at fair value", "Operating"),
            row("Impairment losses/reversals on investment entities / Investment property at fair value", "Operating"),
            row("Net gain/loss on derivatives that hedge operating investments", "Operating"),
            row("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            row("Variable lease payments", "Operating"),
            row("Depreciation of ROU", "Operating"),
            row("Interest expense on lease liability", "Financing"),
            row("Interest income from loans granted to third parties (non-customers)", "Investing"),
            row("Interest expense", "Financing", True),
            row("Income expense", "Financing", True),
            row("FX differences on financing debt", "Financing"),
            row("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            row("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            row("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            row("Impairment losses on equity-accounted investments", "Investing"),
            row("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            row("FX on lease liabilities", "Financing"),
            row("Dividends from associates measured at equity method", "Investing"),
            row("Income tax expense (benefit)", "Income Tax"),
            row("Discontinued operations", "Discontinued Ops"),
        ]

    # --- TEMPLATE 2: FINANCING ENTITY ---
    elif template_name == "Financing Entity":
        data = [
            row("Revenue from the sale of goods or services", "Operating"),
            row("Cost of sales, cost of goods", "Operating", True),
            row("Sales and marketing", "Operating", True),
            row("Research and development", "Operating", True),
            row("General and administrative expenses", "Operating", True),
            row("Other operating expenses", "Operating", True),
            row("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            row("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            row("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            row("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            row("Income or expense form Government grants related to operations", "Operating"),
            row("Interest income on loans to customers", "Operating"),
            row("Interest income on credit facilities to customers", "Operating"),
            row("Interest income on bonds related to financing customers", "Operating"),
            row("Interest expense on customer deposits", "Operating"),
            row("FX differences on trade receivables/payables", "Operating"),
            row("Impairment losses/reversals on trade receivables", "Operating"),
            # Dynamic Policies
            row("Income and expenses from cash and cash equivalents", "Accounting Policy"),
            row("Interest on loans/bonds not related to customer financing", "Accounting Policy"),
            row("FX on customer loans", "Operating"),
            row("Loan origination fees", "Operating"),
            row("Late customers payment penalties", "Operating"),
            row("Expected credit losses from account receviables (AR) (IFRS 9)", "Operating"),
            row("Net gain/loss on derivatives hedging customer loans", "Operating"),
            row("Management fees for servicing customer loans", "Operating"),
            row("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            row("Depreciation of ROU", "Operating"),
            row("Variable lease payments", "Operating"),
            row("Bank fees not related to a specefic borrowing", "Operating"),
            row("FX differences on financing debt used to fund customer loans", "Operating"),
            row("Rental income from investment property", "Investing"),
            row("Fair value gains and losses from investment property", "Investing"),
            row("Dividends recieved from investment entities", "Investing"),
            row("Interest from investment debt securities", "Investing"),
            row("Net gain / loss on investment entites at fair value", "Investing"),
            row("Gain on disposal of investment entities / Investment property at fair value", "Investing"),
            row("Realized FX gains/losses on investment entities / Investment property at fair value", "Investing"),
            row("Impairment losses/reversals on investment entities / Investment property at fair value", "Investing"),
            row("Net gain/loss on derivatives that hedge investment assets", "Investing"),
            row("Interest expense on lease liability", "Financing"),
            row("Interest income from loans granted to third parties (non-customers)", "Investing"),
            row("Other Interest expense", "Financing", True),
            row("Other Income expense", "Financing", True),
            row("FX differences on financing debt", "Financing"),
            row("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            row("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            row("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            row("Impairment losses on equity-accounted investments", "Investing"),
            row("Dividends from associates measured at equity method", "Investing"),
            row("FX on lease liabilities", "Financing"),
            row("Interest expenses on a contract liability with a significant financing component", "Financing"),
            row("FX differences on loans received from third parties", "Financing"),
            row("Interest expense arise from lease liabilities", "Financing"),
            row("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            row("Income tax expense (benefit)", "Income Tax"),
            row("Discontinued operations", "Discontinued Ops"),
        ]

    # --- TEMPLATE 3: OTHER / GENERAL ---
    else:
        data = [
            row("Revenue from the sale of goods or services", "Operating"),
            row("Cost of sales, cost of goods", "Operating", True),
            row("Sales and marketing", "Operating", True),
            row("Research and development", "Operating", True),
            row("General and administrative expenses", "Operating", True),
            row("Other operating expenses", "Operating", True),
            row("Depreciation, impairment and impairment reversals of property, plant and equipment", "Operating"),
            row("Amortisation, impairment and impairment reversals of intangibles", "Operating"),
            row("Gains and losses on the disposal of property, plant and equipment or intangibles", "Operating"),
            row("Foreign exchange differences arised from trade receivable denominated in a foreign currency", "Operating"),
            row("Income or expense form Government grants related to operations", "Operating"),
            row("FX differences on trade receivables/payables", "Operating"),
            row("Impairment losses/reversals on trade receivables", "Operating"),
            row("Rental income from property used in operations/ Investment property", "Investing"),
            row("Gain or loss on lease modifications or remeasurements related to ROU", "Operating"),
            row("Depreciation of ROU", "Operating"),
            row("Interest expense from lease liabilities", "Financing"),
            row("Interest expenses on trade payables", "Operating"),
            row("Variable lease payments", "Operating"),
            row("Bank fees not related to a specefic borrowing", "Operating"),
            row("Fair value gains and losses from investment property", "Investing"),
            row("Dividends recieved from investment entities", "Investing"),
            row("Interest from investment debt securities", "Investing"),
            row("Net gain / loss on investment entites at fair value", "Investing"),
            row("Gain on disposal of investment entities / Investment property at fair value", "Investing"),
            row("Realized FX gains/losses on investment entities / Investment property at fair value", "Investing"),
            row("Impairment losses/reversals on investment entities / Investment property at fair value", "Investing"),
            row("Net gain/loss on derivatives that hedge investment assets", "Investing"),
            row("Interest expense on lease liability", "Financing"),
            row("Interest income from loans granted to third parties (non-customers)", "Investing"),
            row("Interest expense", "Financing", True),
            row("Income expense", "Financing", True),
            row("FX differences on financing debt", "Financing"),
            row("Fair value changes on derivatives used solely to hedge financing debt", "Financing"),
            row("Fair value gains and losses on a liability designated at fair value through profit or loss", "Financing"),
            row("Share of profit/loss from associates or joint ventures – equity method (IAS 28)", "Investing"),
            row("Impairment losses on equity-accounted investments", "Investing"),
            row("Dividends from associates measured at equity method", "Investing"),
            row("Income and expenses from cash and cash equivalents", "Investing"),
            row("FX on lease liabilities", "Financing"),
            row("Interest expense on loans received from third party", "Financing"),
            row("FX differences on loans received from third parties", "Financing"),
            row("Net interest expense (income) on a net defined benefit liability (asset)", "Financing"),
            row("Interest expenses on a contract liability with a significant financing component", "Financing"),
            row("Income tax expense (benefit)", "Income Tax"),
            row("Discontinued operations", "Discontinued Ops"),
        ]
        
    return pd.DataFrame(data)

def get_final_category(row_data, policies):
    """Determines the final category based on static mapping + policies."""
    cat = row_data["Default Category"]
    name = row_data["Line Item"].lower()
    
    if cat == "Accounting Policy":
        if "cash and cash equivalents" in name:
            return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
        if "loans/bonds not related" in name:
            return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
    
    return cat

# --- 5. State Initialization ---
if "step" not in st.session_state: st.session_state.step = 1
if "template_key" not in st.session_state: st.session_state.template_key = "Other main buisness activities"
if "p_cash" not in st.session_state: st.session_state.p_cash = "No"
if "p_fin" not in st.session_state: st.session_state.p_fin = "No"

# --- 6. UI Steps ---

def render_sidebar():
    with st.sidebar:
        st.markdown("### Process Status")
        steps = ["Upload", "Business Model", "Mapping", "Redistribution", "Final Report"]
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
    
    # Logic
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
    if b2.button("Confirm & Map →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    st.subheader("3. Map Line Items")
    st.write("Link your source lines to the IFRS 18 template. **Select 'Yes' to Ungroup/Split** lines.")
    
    df = st.session_state.uploaded_df
    # Load correct template data
    ref_df = get_template_data(st.session_state.template_key)
    
    # Sort: Put [G] Groups at the top for easier initial mapping
    options = ref_df.sort_values("Is Group", ascending=False)["Display Name"].tolist()
    
    if "mapping_df" not in st.session_state:
        m = []
        for line in df["line item"]:
            # Fuzzy match against the full list
            best_match, _, _ = process.extractOne(str(line), options, scorer=fuzz.token_sort_ratio)
            m.append({"uploaded_line": line, "target_line": best_match, "Ungroup": "No"})
        st.session_state.mapping_df = pd.DataFrame(m)

    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "target_line": st.column_config.SelectboxColumn("IFRS 18 Group/Line", options=options, width="large"),
            "Ungroup": st.column_config.SelectboxColumn("Ungroup?", options=["No", "Yes"], width="small")
        },
        use_container_width=True, hide_index=True, height=500, key="editor_map"
    )
    st.session_state.mapping_df = edited
    
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 2; st.rerun()
    
    has_ungroup = any(edited["Ungroup"] == "Yes")
    lbl = "Proceed to Redistribution →" if has_ungroup else "Generate Report →"
    if b2.button(lbl):
        st.session_state.step = 4 if has_ungroup else 5
        st.rerun()

def step_4_redistribute():
    st.subheader("4. Granular Redistribution")
    st.info("Allocate amounts from grouped lines into specific detail lines.")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    year_cols = [c for c in df.columns if c != "line item"]
    
    # Load Template again to get NON-Group lines for the dropdown
    ref_df = get_template_data(st.session_state.template_key)
    # Filter for DETAILED lines (Is Group = False) for allocation targets
    detailed_options = ref_df[~ref_df["Is Group"]]["Display Name"].tolist()
    
    ungroup_rows = mapping[mapping["Ungroup"] == "Yes"]
    if ungroup_rows.empty: st.session_state.step = 5; st.rerun()
    
    alloc_list = []
    tabs = st.tabs([f"📝 {r['uploaded_line']}" for _, r in ungroup_rows.iterrows()])
    
    for i, tab in enumerate(tabs):
        with tab:
            row = ungroup_rows.iloc[i]
            src = row['uploaded_line']
            orig_vals = df[df["line item"] == src].iloc[0][year_cols]
            
            c1, c2 = st.columns([1, 3])
            c1.markdown(f"**Source:** `{src}`")
            for y in year_cols: c1.metric(y, f"{orig_vals[y]:,.0f}")
            
            key = f"alloc_{src}_{i}"
            if key not in st.session_state:
                # Default to first detailed line
                st.session_state[key] = pd.DataFrame([{"New IFRS Line": detailed_options[0], **{y: 0.0 for y in year_cols}}])
            
            with c2:
                edited = st.data_editor(
                    st.session_state[key],
                    column_config={"New IFRS Line": st.column_config.SelectboxColumn(options=detailed_options, width="large")},
                    num_rows="dynamic", use_container_width=True, key=f"wid_{key}"
                )
                st.session_state[key] = edited
                
                diffs = orig_vals - edited[year_cols].sum()
                if all(abs(d) < 1 for d in diffs): st.success("Balanced ✅")
                else: st.warning("⚠️ Remainder exists")
            
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
    
    # 1. Get Template & Logic
    ref_df = get_template_data(st.session_state.template_key)
    policies = {"cash_op": st.session_state.p_cash, "fin_op": st.session_state.p_fin}
    
    # Resolve Categories dynamically
    ref_df["Final Category"] = ref_df.apply(lambda r: get_final_category(r, policies), axis=1)
    
    # 2. Build Result Container
    # We use "Line Item" as the key, "Display Name" is just for UI
    final = pd.DataFrame(index=ref_df["Line Item"].unique())
    # Map back category
    cat_map = ref_df.set_index("Line Item")["Final Category"].to_dict()
    final["Category"] = final.index.map(cat_map)
    for y in year_cols: final[y] = 0.0
    
    sankey_data = []

    # 3. Process Data
    # Standard Mappings
    for _, m in mapping.iterrows():
        if m["Ungroup"] == "No":
            src = m["uploaded_line"]
            # Remove [G] prefix to find in index
            target_clean = m["target_line"].replace("[G] ", "")
            
            vals = df[df["line item"] == src].iloc[0][year_cols]
            if target_clean in final.index:
                for y in year_cols: final.at[target_clean, y] += vals[y]
                # Sankey Log
                if vals[year_cols[0]] != 0:
                    sankey_data.append({"Source": src, "Target": final.loc[target_clean, "Category"], "Value": abs(vals[year_cols[0]])})

    # Allocations
    if not allocs.empty:
        for _, r in allocs.iterrows():
            target_clean = r["New IFRS Line"].replace("[G] ", "")
            if target_clean in final.index:
                for y in year_cols: final.at[target_clean, y] += r[y]
                # Sankey Log
                if r[year_cols[0]] != 0:
                    sankey_data.append({"Source": r["_source"], "Target": final.loc[target_clean, "Category"], "Value": abs(r[year_cols[0]])})

    # 4. Format Output
    def get_tot(cat): return final[final["Category"] == cat][year_cols].sum()
    
    pl_rows = []
    
    # -- Operating --
    pl_rows.append({"Line Item": "<b>OPERATING CATEGORY</b>", "Header": True})
    op_subset = final[final["Category"] == "Operating"]
    op_subset = op_subset[op_subset[year_cols].abs().sum(axis=1) > 0.01] # Hide empty
    for idx, r in op_subset.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    op_tot = get_tot("Operating")
    d_op = {"Line Item": "<b>Operating Profit or Loss</b>", "Total": True}; d_op.update(op_tot.to_dict())
    pl_rows.append(d_op)
    
    # -- Investing --
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>INVESTING CATEGORY</b>", "Header": True})
    inv_subset = final[final["Category"] == "Investing"]
    inv_subset = inv_subset[inv_subset[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in inv_subset.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    inv_tot = get_tot("Investing")
    ebit_tot = op_tot + inv_tot
    d_ebit = {"Line Item": "<b>Profit Before Financing & Tax</b>", "Total": True}; d_ebit.update(ebit_tot.to_dict())
    pl_rows.append(d_ebit)
    
    # -- Financing --
    pl_rows.append({"Line Item": " ", "Header": True})
    pl_rows.append({"Line Item": "<b>FINANCING CATEGORY</b>", "Header": True})
    fin_subset = final[final["Category"] == "Financing"]
    fin_subset = fin_subset[fin_subset[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in fin_subset.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
    fin_tot = get_tot("Financing")
    pbt_tot = ebit_tot + fin_tot
    d_pbt = {"Line Item": "<b>Profit Before Tax</b>", "Total": True}; d_pbt.update(pbt_tot.to_dict())
    pl_rows.append(d_pbt)
    
    # -- Others --
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
        # Clean CSV for download
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
