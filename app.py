import io
import re
import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

# --- 1. Page Config ---
st.set_page_config(
    page_title="IFRS 18 Converter | PwC",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Professional Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
        color: #2D2D2D;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #D04A02; color: white; border-radius: 4px; font-weight: 600; 
        border: none; height: 3em; width: 100%; transition: 0.2s;
    }
    .stButton > button:hover { background-color: #b03d00; color: white; }
    
    /* Sidebar Steps */
    .step-active { color: #D04A02; font-weight: bold; border-left: 4px solid #D04A02; padding-left: 10px; margin-bottom: 10px;}
    .step-inactive { color: #666; padding-left: 14px; margin-bottom: 10px;}
    
    /* Custom Table Styling for Report */
    .pwc-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 16px; /* Bigger font */
        font-family: 'Arial', sans-serif;
        margin-bottom: 30px;
    }
    .pwc-table th {
        background-color: #f2f2f2;
        color: #D04A02;
        padding: 12px;
        text-align: right;
        border-bottom: 2px solid #2D2D2D;
    }
    .pwc-table th:first-child { text-align: left; }
    .pwc-table td {
        padding: 10px;
        border-bottom: 1px solid #e0e0e0;
    }
    .pwc-header {
        background-color: #ffffff;
        font-weight: bold;
        color: #D04A02;
        text-transform: uppercase;
        border-bottom: 2px solid #D04A02;
    }
    .pwc-total {
        font-weight: bold;
        background-color: #fafafa;
        border-top: 2px solid #2D2D2D;
    }
    .pwc-grand {
        font-weight: bold;
        font-size: 18px;
        background-color: #e8e8e8;
        border-top: 2px solid #2D2D2D;
        border-bottom: 4px double #2D2D2D;
    }
    .num-cell { font-family: 'Courier New', monospace; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Helpers ---

def render_header():
    c1, c2 = st.columns([0.6, 4])
    with c1:
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=120)
    with c2:
        st.markdown("## IFRS 18 Financial Statement Converter")
        st.caption("Professional Template Allocation Engine")
    st.divider()

def clean_val(x):
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    if s in ['nan', '—', '-', '']: return 0.0
    if '(' in s: s = '-' + s.replace('(', '').replace(')', '')
    s = re.sub(r'[^\d\.\-]', '', s)
    try: return float(s)
    except: return 0.0

def load_data(file):
    try:
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    except: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    possible = ["line item", "description", "account", "label"]
    line_col = next((c for c in df.columns if c.lower() in possible), df.columns[0])
    df = df.rename(columns={line_col: "line item"})
    valid_cols = ["line item"]
    for c in df.columns:
        if c == "line item": continue
        clean = str(c).replace(',', '').replace('.', '')
        if len(clean) == 4 and clean.isdigit():
            valid_cols.append(c)
            df[c] = df[c].apply(clean_val)
    return df[valid_cols]

# --- 4. Templates ---

def get_full_template(key):
    base = [
        "Revenue from the sale of goods or services",
        "Cost of sales, cost of goods",
        "Sales and marketing",
        "Research and development",
        "General and administrative expenses",
        "Other operating expenses",
        "Depreciation, impairment and impairment reversals of property, plant and equipment",
        "Amortisation, impairment and impairment reversals of intangibles",
        "Gains and losses on the disposal of property, plant and equipment or intangibles",
        "Foreign exchange differences arised from trade receivable denominated in a foreign currency",
        "Income or expense form Government grants related to operations",
        "FX differences on trade receivables/payables",
        "Impairment losses/reversals on trade receivables",
        "Income tax expense (benefit)",
        "Discontinued operations"
    ]

    investing_add = [
        "Interest expense", "Income expense", 
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
        "Dividends from associates measured at equity method"
    ]

    financing_add = [
        "Other Interest expense", "Other Income expense",
        "Interest income on loans to customers",
        "Interest income on credit facilities to customers",
        "Interest income on bonds related to financing customers",
        "Interest expense on customer deposits",
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
        "Net interest expense (income) on a net defined benefit liability (asset)"
    ]

    general_add = [
        "Interest expense", "Income expense",
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
        "Interest expenses on a contract liability with a significant financing component"
    ]

    if key == "Investing Entity": return sorted(list(set(base + investing_add)))
    if key == "Financing Entity": return sorted(list(set(base + financing_add)))
    return sorted(list(set(base + general_add)))

def get_category(line, key, policies):
    l = line.lower()
    if "tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    if key == "Financing Entity":
        if "cash" in l: return "Operating" if policies.get("cash_op") == "Yes" else "Investing"
        if "not related to customer" in l: return "Operating" if policies.get("fin_op") == "Yes" else "Financing"
        if "customer" in l or "loans" in l: return "Operating"
    if "interest expense" in l or "financing" in l or "lease" in l: return "Financing"
    if "invest" in l or "dividend" in l or "equity" in l: return "Investing"
    return "Operating"

# --- 5. State Management ---

if "step" not in st.session_state: st.session_state.step = 1
# This dictionary will hold our "Database" so it doesn't reset
if "data_store" not in st.session_state: st.session_state.data_store = {
    "uploaded_df": None,
    "template_key": "Other main buisness activities",
    "p_cash": "No",
    "p_fin": "No",
    "mapping_df": None
}

# --- 6. Steps ---

def render_sidebar():
    with st.sidebar:
        st.markdown("### Workflow")
        steps = ["Upload", "Business Model", "Allocation", "Report"]
        for i, s in enumerate(steps, 1):
            cls = "step-active" if st.session_state.step == i else "step-inactive"
            st.markdown(f"<div class='{cls}'>{i}. {s}</div>", unsafe_allow_html=True)
        st.divider()
        if st.button("Reset Application"): 
            st.session_state.data_store = {"uploaded_df": None, "template_key": "Other", "p_cash": "No", "p_fin": "No", "mapping_df": None}
            st.session_state.step = 1
            st.rerun()

def step_1():
    st.subheader("1. Upload P&L Data")
    f = st.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])
    if f:
        df = load_data(f)
        if not df.empty:
            # Save to Store
            st.session_state.data_store["uploaded_df"] = df
            st.session_state.data_store["mapping_df"] = None
            st.toast("File uploaded successfully!", icon="✅")
            
            # --- Completeness Check ---
            st.markdown("### Completeness Check")
            st.metric("Total Lines Loaded", len(df))
            st.dataframe(df, use_container_width=True, height=400)
            
            if st.button("Next: Business Model →"): st.session_state.step = 2; st.rerun()

def step_2():
    st.subheader("2. Business Model Assessment")
    
    ds = st.session_state.data_store
    
    q1 = st.radio("Does the entity invest in financial assets as a main activity?", ["No", "Yes"], index=0, key="q1")
    q2 = st.radio("Does the entity provide financing to customers as a main activity?", ["No", "Yes"], index=0, key="q2")
    
    temp = "Other main buisness activities"
    if q1 == "Yes": temp = "Investing Entity"
    elif q2 == "Yes": temp = "Financing Entity"
    
    p_cash, p_fin = "No", "No"
    if temp == "Financing Entity":
        st.markdown("##### Policies")
        c1, c2 = st.columns(2)
        with c1: p_cash = st.radio("Classify Cash as Operating?", ["Yes", "No"], key="p1")
        with c2: p_fin = st.radio("Classify Non-Customer Interest as Operating?", ["Yes", "No"], index=1, key="p2")

    c1, c2 = st.columns([1, 5])
    if c1.button("← Back"): st.session_state.step = 1; st.rerun()
    
    if c2.button("Show Template & Allocate →"):
        # Save decisions
        ds["template_key"] = temp
        ds["p_cash"] = p_cash
        ds["p_fin"] = p_fin
        
        # PRE-GENERATE TABLE
        df = ds["uploaded_df"]
        year_cols = [c for c in df.columns if c != "line item"]
        template_lines = get_full_template(temp)
        source_options = sorted(df["line item"].unique().tolist())
        
        rows = []
        for t_line in template_lines:
            best, score, _ = process.extractOne(t_line, source_options, scorer=fuzz.token_sort_ratio)
            src_guess = best if score > 60 else None
            row = {
                "Include?": False,
                "IFRS 18 Line Item": t_line,
                "Map from Source": src_guess
            }
            for y in year_cols: row[y] = 0.0
            rows.append(row)
            
        ds["mapping_df"] = pd.DataFrame(rows)
        st.session_state.step = 3
        st.rerun()

def step_3():
    st.subheader("3. Template Allocation")
    st.info("Select IFRS 18 lines and map them to your source file.")
    
    ds = st.session_state.data_store
    df = ds["uploaded_df"]
    year_cols = [c for c in df.columns if c != "line item"]
    source_options = ["(None)"] + sorted(df["line item"].unique().tolist())
    
    # Auto-Fill
    if st.button("Auto-Fill Amounts for Mapped Lines"):
        curr_df = ds["mapping_df"]
        for idx, row in curr_df.iterrows():
            src = row["Map from Source"]
            if src and src in source_options:
                src_vals = df[df["line item"] == src].iloc[0]
                for y in year_cols: curr_df.at[idx, y] = src_vals[y]
                curr_df.at[idx, "Include?"] = True
        ds["mapping_df"] = curr_df
        st.success("Amounts filled!")
        st.rerun()

    # Editor
    edited_df = st.data_editor(
        ds["mapping_df"],
        column_config={
            "Include?": st.column_config.CheckboxColumn(width="small"),
            "IFRS 18 Line Item": st.column_config.TextColumn(disabled=True, width="large"),
            "Map from Source": st.column_config.SelectboxColumn(options=source_options, width="medium"),
            **{y: st.column_config.NumberColumn(format="%.0f") for y in year_cols}
        },
        height=600,
        use_container_width=True,
        hide_index=True,
        key="master_editor_key"
    )
    
    ds["mapping_df"] = edited_df

    c1, c2 = st.columns([1, 5])
    if c1.button("← Back"): st.session_state.step = 2; st.rerun()
    if c2.button("Generate Final Report →"): st.session_state.step = 4; st.rerun()

def step_4():
    st.subheader("4. Consolidated IFRS 18 Report")
    
    ds = st.session_state.data_store
    mapping_data = ds["mapping_df"]
    df = ds["uploaded_df"] 
    year_cols = [c for c in df.columns if c != "line item"]
    key = ds["template_key"]
    policies = {"cash_op": ds["p_cash"], "fin_op": ds["p_fin"]}
    
    # --- LOGIC: Combine Allocated Lines + Unallocated Remainders ---
    final_rows = []
    audit_trail = [] # For the summary table
    
    # 1. Process Mapped Lines (Details)
    included = mapping_data[mapping_data["Include?"] == True]
    
    for _, row in included.iterrows():
        is_val = sum([abs(float(row.get(y, 0))) for y in year_cols]) > 0
        if is_val:
            cat = get_category(row["IFRS 18 Line Item"], key, policies)
            d = {"Line Item": row["IFRS 18 Line Item"], "Category": cat}
            for y in year_cols: d[y] = float(row.get(y, 0))
            final_rows.append(d)
            
            # Add to Audit Trail
            src_lbl = row["Map from Source"] if row["Map from Source"] else "Direct Entry"
            audit_trail.append({"IFRS 18 Line": row["IFRS 18 Line Item"], "Source": src_lbl, "Amount": d[year_cols[0]]})
            
    # 2. Process Remainders (Groups)
    rem_df = df.set_index("line item")[year_cols].copy()
    for _, row in included.iterrows():
        src = row["Map from Source"]
        if src != "(None)" and src in rem_df.index:
            for y in year_cols:
                rem_df.at[src, y] -= float(row.get(y, 0))
                
    for idx, r in rem_df.iterrows():
        if r.abs().sum() > 0.1:
            d = {"Line Item": f"[Group] {idx}", "Category": "Operating"}
            d.update(r.to_dict())
            final_rows.append(d)
            
            audit_trail.append({"IFRS 18 Line": f"[Group] {idx}", "Source": "Unallocated Remainder", "Amount": r[year_cols[0]]})
            
    final_df = pd.DataFrame(final_rows)
    
    if final_df.empty:
        st.warning("No data generated.")
        return

    # --- HTML RENDERER ---
    
    def generate_html_table(df_pl, years):
        def fmt_num(n): return f"({abs(n):,.0f})" if n < 0 else f"{n:,.0f}" if n != 0 else "-"
        
        def get_subtotal(cat):
            if "Category" not in df_pl.columns: return pd.Series(0, index=years)
            return df_pl[df_pl["Category"] == cat][years].sum()

        html = '<table class="pwc-table">'
        # Header
        html += '<thead><tr><th>Line Item</th>' + ''.join([f'<th>{y}</th>' for y in years]) + '</tr></thead><tbody>'
        
        sections = [("Operating", "OPERATING CATEGORY"), ("Investing", "INVESTING CATEGORY"), ("Financing", "FINANCING CATEGORY")]
        
        # Calculations
        op_tot = get_subtotal("Operating")
        inv_tot = get_subtotal("Investing")
        fin_tot = get_subtotal("Financing")
        ebit = op_tot + inv_tot
        pbt = ebit + fin_tot
        
        # Loop Sections
        for cat_key, cat_name in sections:
            html += f'<tr class="pwc-header"><td colspan="{1+len(years)}">{cat_name}</td></tr>'
            if "Category" in df_pl.columns:
                subset = df_pl[df_pl["Category"] == cat_key]
                for _, r in subset.iterrows():
                    html += f'<tr><td>{r["Line Item"]}</td>' + ''.join([f'<td class="num-cell">{fmt_num(r[y])}</td>' for y in years]) + '</tr>'
            
            # Subtotals
            if cat_key == "Operating":
                html += '<tr class="pwc-total"><td>Operating Profit or Loss</td>' + ''.join([f'<td class="num-cell">{fmt_num(op_tot[y])}</td>' for y in years]) + '</tr>'
            elif cat_key == "Investing":
                html += '<tr class="pwc-total"><td>Profit Before Financing & Tax</td>' + ''.join([f'<td class="num-cell">{fmt_num(ebit[y])}</td>' for y in years]) + '</tr>'
            elif cat_key == "Financing":
                html += '<tr class="pwc-total"><td>Profit Before Tax</td>' + ''.join([f'<td class="num-cell">{fmt_num(pbt[y])}</td>' for y in years]) + '</tr>'

        # Tax & Disc
        tax = get_subtotal("Income Tax")
        if tax.abs().sum() > 0:
            html += f'<tr><td>Income Tax Expense</td>' + ''.join([f'<td class="num-cell">{fmt_num(tax[y])}</td>' for y in years]) + '</tr>'
        
        disc = get_subtotal("Discontinued Ops")
        if disc.abs().sum() > 0:
            html += f'<tr><td>Discontinued Operations</td>' + ''.join([f'<td class="num-cell">{fmt_num(disc[y])}</td>' for y in years]) + '</tr>'
            
        grand = final_df[years].sum()
        html += '<tr class="pwc-grand"><td>PROFIT OR LOSS</td>' + ''.join([f'<td class="num-cell">{fmt_num(grand[y])}</td>' for y in years]) + '</tr>'
        
        html += '</tbody></table>'
        return html

    st.markdown(generate_html_table(final_df, year_cols), unsafe_allow_html=True)
    
    # Download Button
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Final Report", csv, "IFRS18_P&L.csv", "text/csv")
    
    st.divider()
    
    # --- SUMMARY TABLE ---
    st.subheader("Composition Breakdown")
    st.write("Details of source mapping and inserted lines.")
    audit_df = pd.DataFrame(audit_trail)
    if not audit_df.empty:
        st.dataframe(audit_df, use_container_width=True)

    if st.button("Start Over"): st.session_state.clear(); st.rerun()

# --- Main ---
def main():
    render_header()
    render_sidebar()
    if st.session_state.step == 1: step_1()
    elif st.session_state.step == 2: step_2()
    elif st.session_state.step == 3: step_3()
    elif st.session_state.step == 4: step_4()

if __name__ == "__main__":
    main()
