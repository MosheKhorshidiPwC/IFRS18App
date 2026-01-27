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

# --- 5. Template Definitions (The Core Data) ---

def get_template_lines(key):
    """Returns the exact list of lines based on the selected business model."""
    
    # 1. Investing Entity Template
    if key == "Investing Entity":
        return [
            "Revenue from the sale of goods or services",
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency",
            "Income or expense form Government grants related to operations",
            "FX differences on trade receivables/payables",
            "Impairment losses/reversals on trade receivables",
            "Rental income from investment property",
            "Fair value gains and losses from investment property",
            "Dividends recieved from investment entities",
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
            "Fair value changes on derivatives used solely to hedge financing debt",
            "Fair value gains and losses on a liability designated at fair value through profit or loss",
            "Share of profit/loss from associates or joint ventures – equity method (IAS 28)",
            "Impairment losses on equity-accounted investments",
            "Net interest expense (income) on a net defined benefit liability (asset)",
            "FX on lease liabilities",
            "Dividends from associates measured at equity method",
            "Income tax expense (benefit)",
            "Discontinued operations"
        ]

    # 2. Financing Entity Template
    elif key == "Financing Entity":
        return [
            "Revenue from the sale of goods or services",
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency",
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
            "Management fees for servicing customer loans",
            "Gain or loss on lease modifications or remeasurements related to ROU",
            "Depreciation of ROU",
            "Variable lease payments",
            "Bank fees not related to a specefic borrowing",
            "FX differences on financing debt used to fund customer loans",
            "Rental income from investment property",
            "Fair value gains and losses from investment property",
            "Dividends recieved from investment entities",
            "Interest from investment debt securities",
            "Net gain / loss on investment entites at fair value",
            "Gain on disposal of investment entities / Investment property at fair value",
            "Realized FX gains/losses on investment entities / Investment property at fair value",
            "Impairment losses/reversals on investment entities / Investment property at fair value",
            "Net gain/loss on derivatives that hedge investment assets",
            "Interest expense on lease liability",
            "Interest income from loans granted to third parties (non-customers)",
            "FX differences on financing debt",
            "Fair value changes on derivatives used solely to hedge financing debt",
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

    # 3. General Corporate (Other) Template
    else:
        return [
            "Revenue from the sale of goods or services",
            "Depreciation, impairment and impairment reversals of property, plant and equipment",
            "Amortisation, impairment and impairment reversals of intangibles",
            "Gains and losses on the disposal of property, plant and equipment or intangibles",
            "Foreign exchange differences arised from trade receivable denominated in a foreign currency",
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
            "Fair value gains and losses from investment property",
            "Dividends recieved from investment entities",
            "Interest from investment debt securities",
            "Net gain / loss on investment entites at fair value",
            "Gain on disposal of investment entities / Investment property at fair value",
            "Realized FX gains/losses on investment entities / Investment property at fair value",
            "Impairment losses/reversals on investment entities / Investment property at fair value",
            "Net gain/loss on derivatives that hedge investment assets",
            "Interest expense on lease liability",
            "Interest income from loans granted to third parties (non-customers)",
            "FX differences on financing debt",
            "Fair value changes on derivatives used solely to hedge financing debt",
            "Fair value gains and losses on a liability designated at fair value through profit or loss",
            "Share of profit/loss from associates or joint ventures – equity method (IAS 28)",
            "Impairment losses on equity-accounted investments",
            "Dividends from associates measured at equity method",
            "Income and expenses from cash and cash equivalents",
            "FX on lease liabilities",
            "Interest expense on loans received from third party",
            "FX differences on loans received from third parties",
            "Net interest expense (income) on a net defined benefit liability (asset)",
            "Interest expenses on a contract liability with a significant financing component",
            "Income tax expense (benefit)",
            "Discontinued operations"
        ]

def classify_line(line, key, policies):
    """Categorizes a line item based on the Template and Policies."""
    l = line.lower()
    
    # 1. Income Tax & Discontinued (Universal)
    if "income tax" in l: return "Income Tax"
    if "discontinued operations" in l: return "Discontinued Ops"
    
    # 2. Financing Entity Logic
    if key == "Financing Entity":
        # Policy: Cash & Equivalents
        if "cash and cash equivalents" in l:
            return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
        # Policy: Non-Customer Financing
        if "loans/bonds not related to customer financing" in l:
            return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
        
        # Financing Entity Specifics -> Operating
        if any(x in l for x in ["customer loans", "customer deposits", "financing customers", "credit facilities"]): return "Operating"
    
    # 3. Investing Entity Logic
    if key == "Investing Entity":
        # Investment returns -> Operating
        if any(x in l for x in ["investment property", "investment entities", "investment debt", "dividends recieved", "derivatives that hedge operating investments"]): return "Operating"

    # 4. General Logic (Fallbacks)
    # Financing
    if any(x in l for x in ["financing debt", "lease liability", "lease liabilities", "interest expense", "loans received from third"]): return "Financing"
    
    # Investing (Standard)
    if any(x in l for x in ["associates", "joint ventures", "equity method", "investment property", "investment entities"]): return "Investing"
    
    # Operating (The rest)
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
        steps = ["Upload", "Business Model", "Mapping", "Redistribution", "Final Report"]
        for i, s in enumerate(steps, 1):
            cls = "step-active" if st.session_state.step == i else "step-inactive"
            st.markdown(f"<div class='{cls}'>{i}. {s}</div>", unsafe_allow_html=True)
        st.divider()
        st.info("Selections are auto-saved.")

def step_1_upload():
    st.subheader("1. Upload Financial Data")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        f = st.file_uploader("", type=['xlsx', 'csv'])
        if f:
            df = load_data_file(f)
            if not df.empty and len(df.columns) > 1:
                st.session_state.uploaded_df = df
                st.toast("Upload Successful!", icon="✅")
    with col2:
        if "uploaded_df" in st.session_state:
            st.markdown(f"**Loaded:** {st.session_state.uploaded_df.shape[0]} lines")
            st.dataframe(st.session_state.uploaded_df.head(5), use_container_width=True, height=200)
            if st.button("Next: Business Model →"):
                st.session_state.step = 2
                st.rerun()

def step_2_model():
    st.subheader("2. Business Model Assessment")
    
    # 1. Investing
    q1 = st.radio("Does the entity invest in financial assets as a main business activity?", 
                  ["No", "Yes"], index=0, key="rad_q1")
    
    # 2. Financing
    q2 = st.radio("Does the entity provide financing to customers as a main business activity?", 
                  ["No", "Yes"], index=0, key="rad_q2")
    
    # Determine Template
    if q1 == "Yes": temp = "Investing Entity"
    elif q2 == "Yes": temp = "Financing Entity"
    else: temp = "Other main buisness activities"
    
    st.session_state.template_key = temp
    
    # Policies for Financing
    if temp == "Financing Entity":
        st.markdown("---")
        st.markdown("##### Accounting Policies")
        c1, c2 = st.columns(2)
        with c1:
            # Policy 1
            st.markdown("**Income/Exp from Cash & Equivalents**")
            p1 = st.radio("Classify as Operating?", ["Yes", "No (Investing)"], key="rad_p1")
            st.session_state.p_cash = "Yes" if "Yes" in p1 else "No"
        with c2:
            # Policy 2
            st.markdown("**Interest on Non-Customer Financing**")
            p2 = st.radio("Classify as Operating?", ["Yes", "No (Financing)"], index=1, key="rad_p2")
            st.session_state.p_fin = "Yes" if "Yes" in p2 else "No"

    st.success(f"Selected Template: **{temp}**")
    
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 1; st.rerun()
    if b2.button("Confirm & Map →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    st.subheader("3. Map Line Items")
    st.write("Match source lines to IFRS 18. **Select 'Yes' to Ungroup** complex lines.")
    
    df = st.session_state.uploaded_df
    # Get the specific list for this template
    targets = get_template_lines(st.session_state.template_key)
    
    if "mapping_df" not in st.session_state:
        m = []
        for line in df["line item"]:
            best, _, _ = process.extractOne(str(line), targets, scorer=fuzz.token_sort_ratio)
            m.append({"uploaded_line": line, "target_line": best, "Ungroup": "No"})
        st.session_state.mapping_df = pd.DataFrame(m)

    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "target_line": st.column_config.SelectboxColumn("IFRS 18 Target", options=targets),
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
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    targets = get_template_lines(st.session_state.template_key)
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
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"**Source:** `{src}`")
                for y in year_cols: st.metric(y, f"{orig_vals[y]:,.0f}")
            
            key = f"alloc_{src}_{i}"
            if key not in st.session_state:
                st.session_state[key] = pd.DataFrame([{"New IFRS Line": targets[0], **{y: 0.0 for y in year_cols}}])
            
            with c2:
                edited = st.data_editor(
                    st.session_state[key],
                    column_config={"New IFRS Line": st.column_config.SelectboxColumn(options=targets, width="large")},
                    num_rows="dynamic", use_container_width=True, key=f"wid_{key}"
                )
                st.session_state[key] = edited
                
                # Check balance
                diffs = orig_vals - edited[year_cols].sum()
                if all(abs(d) < 1 for d in diffs): st.success("Balanced ✅")
                else: st.error("Remainder exists ⚠️")
            
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
    st.subheader("5. IFRS 18 Consolidated Statement of Profit or Loss")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    allocs = st.session_state.get("final_alloc", pd.DataFrame())
    year_cols = [c for c in df.columns if c != "line item"]
    
    key = st.session_state.template_key
    policies = {"cash_op": st.session_state.p_cash, "fin_op": st.session_state.p_fin}
    
    # 1. Prepare Structure
    lines = get_template_lines(key)
    final = pd.DataFrame({"line item": lines})
    # Maintain original order from the prompt list by using the index
    final["_sort"] = final.index 
    final["Category"] = final["line item"].apply(lambda x: classify_line(x, key, policies))
    final = final.set_index("line item")
    for y in year_cols: final[y] = 0.0
    
    # Sankey Data
    sankey_data = []

    # 2. Fill Data
    # Standard
    for _, m in mapping.iterrows():
        if m["Ungroup"] == "No":
            src, target = m["uploaded_line"], m["target_line"]
            vals = df[df["line item"] == src].iloc[0][year_cols]
            if target in final.index:
                for y in year_cols: final.at[target, y] += vals[y]
                if vals[year_cols[0]] != 0:
                    sankey_data.append({"Source": src, "Target": final.loc[target, "Category"], "Value": abs(vals[year_cols[0]])})

    # Allocations
    if not allocs.empty:
        for _, r in allocs.iterrows():
            target = r["New IFRS Line"]
            if target in final.index:
                for y in year_cols: final.at[target, y] += r[y]
                if r[year_cols[0]] != 0:
                    sankey_data.append({"Source": r["_source"], "Target": final.loc[target, "Category"], "Value": abs(r[year_cols[0]])})

    # 3. Format P&L (Subtotals & Ordering)
    
    def get_tot(cat): return final[final["Category"] == cat][year_cols].sum()
    
    pl_rows = []
    
    # Operating
    pl_rows.append({"Line Item": "<b>OPERATING CATEGORY</b>", "Header": True})
    op_df = final[final["Category"] == "Operating"].sort_values("_sort")
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
    inv_df = final[final["Category"] == "Investing"].sort_values("_sort")
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
    fin_df = final[final["Category"] == "Financing"].sort_values("_sort")
    fin_df = fin_df[fin_df[year_cols].abs().sum(axis=1) > 0.01]
    for idx, r in fin_df.iterrows():
        d = {"Line Item": idx}; d.update(r[year_cols].to_dict())
        pl_rows.append(d)
        
    fin_tot = get_tot("Financing")
    pbt_tot = ebit_tot + fin_tot
    d_pbt = {"Line Item": "<b>Profit Before Tax</b>", "Total": True}; d_pbt.update(pbt_tot.to_dict())
    pl_rows.append(d_pbt)
    
    # Tax & Disc
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
    
    # 4. Render
    display = pd.DataFrame(pl_rows)
    
    def fmt(v): 
        if pd.isna(v) or isinstance(v, str): return v
        if v == 0: return "-"
        s = "{:,.0f}".format(abs(v))
        return f"({s})" if v < 0 else s
    
    def style_row(row):
        css = []
        if row.get("Header"): return ['background-color: #f4f4f4; font-weight: bold; border-bottom: 2px solid #333; color: #D04A02'] * len(row)
        if row.get("Grand"): return ['background-color: #e6f2ff; font-weight: bold; border-top: 2px solid #333; border-bottom: 4px double #333'] * len(row)
        if row.get("Total"): return ['font-weight: bold; border-top: 1px solid #333; background-color: white'] * len(row)
        return ['background-color: white'] * len(row)

    # Format values
    view = display.copy()
    for y in year_cols: view[y] = view[y].apply(fmt)
    view = view.drop(columns=["Header", "Total", "Grand"], errors="ignore")
    
    t1, t2 = st.tabs(["📄 Financial Statement", "📊 Flow Analysis"])
    with t1:
        st.write(
            display.style.apply(style_row, axis=1)
            .format({y: fmt for y in year_cols})
            .hide(axis="index").hide(subset=["Header", "Total", "Grand"], axis="columns").to_html(),
            unsafe_allow_html=True
        )
        csv = view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report", csv, "IFRS18_P&L.csv", "text/csv")

    with t2:
        if sankey_data:
            sdf = pd.DataFrame(sankey_data).groupby(["Source", "Target"]).sum().reset_index()
            # Sankey
            lbls = list(pd.concat([sdf["Source"], sdf["Target"]]).unique())
            imap = {l: i for i, l in enumerate(lbls)}
            fig = go.Figure(data=[go.Sankey(
                node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=lbls, color="#D04A02"),
                link=dict(source=sdf["Source"].map(imap), target=sdf["Target"].map(imap), value=sdf["Value"])
            )])
            fig.update_layout(title="Source -> Category Flow")
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
