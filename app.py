import io
import re
import time
from typing import List, Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from rapidfuzz import process, fuzz
import streamlit as st

# --- 1. Page Configuration (Must be first) ---
st.set_page_config(
    page_title="IFRS 18 Insights | PwC",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Professional Styling (CSS Injection) ---
st.markdown("""
    <style>
    /* Global Font & Colors */
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    /* PwC Colors: Orange #D04A02, Black #2D2D2D, Grey #F2F2F2 */
    
    /* Header Bar */
    .header-bar {
        padding: 1rem 0rem;
        border-bottom: 2px solid #D04A02;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
    }
    
    /* Metric Cards */
    div.css-1r6slb0.e1tzin5v2 {
        background-color: #F9F9F9;
        border: 1px solid #E0E0E0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #2D2D2D;
        color: white;
        border-radius: 4px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #D04A02;
        color: white;
        transform: translateY(-2px);
    }
    
    /* Step Indicators */
    .step-active {
        color: #D04A02;
        font-weight: bold;
        border-left: 4px solid #D04A02;
        padding-left: 10px;
    }
    .step-inactive {
        color: #888;
        padding-left: 14px;
    }
    
    /* Success/Info Boxes */
    .stAlert {
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Logic & Helpers ---

def render_header():
    col1, col2 = st.columns([0.5, 4])
    with col1:
        # Placeholder for PwC Logo - using a generic professional icon or link
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/05/PricewaterhouseCoopers_Logo.svg", width=140)
    with col2:
        st.markdown("""
            <h2 style='margin-bottom: 0; color: #2D2D2D;'>IFRS 18 Financial Statement Converter</h2>
            <p style='margin-top: 0; color: #666;'>Automated classification, mapping, and ungrouping engine.</p>
        """, unsafe_allow_html=True)
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
    grouped = [
        "Revenue from the sale of goods or services", "Cost of sales, cost of goods", 
        "Sales and marketing", "Research and development", 
        "General and administrative expenses", "Other operating expenses"
    ]
    detailed = [
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
    return grouped, detailed

def classify_category(line, template_key, policies):
    l = line.lower()
    if "cash" in l and "equivalents" in l: return "Operating" if policies.get("cash_is_operating") == "Yes" else "Investing"
    if "non-customer financing" in l or "loans/bonds not related" in l: return "Operating" if policies.get("finance_is_operating") == "Yes" else "Financing"
    if any(x in l for x in ["revenue", "cost of sales", "sales and marketing", "research", "general and admin", "operating"]): return "Operating"
    if "tax" in l: return "Income Tax"
    if "discontinued" in l: return "Discontinued Ops"
    if any(x in l for x in ["financing", "lease liability", "interest expense"]): return "Financing"
    if any(x in l for x in ["associates", "equity method", "dividends"]): return "Investing"
    if template_key == "Investing Entity" and ("interest income" in l or "fair value" in l): return "Operating"
    if template_key == "Financing Entity" and ("interest income" in l or "impairment" in l): return "Operating"
    return "Operating"

# --- State Initialization ---
if "step" not in st.session_state: st.session_state.step = 1
if "template_key" not in st.session_state: st.session_state.template_key = "General Corporate"
if "policy_cash" not in st.session_state: st.session_state.policy_cash = "No"
if "policy_finance" not in st.session_state: st.session_state.policy_finance = "No"

# --- UI Steps ---

def render_sidebar():
    with st.sidebar:
        st.markdown("### Process Status")
        steps = ["Data Upload", "Business Model", "Mapping", "Redistribution", "Final Report"]
        for i, s in enumerate(steps, 1):
            if st.session_state.step == i:
                st.markdown(f"<div class='step-active'>{i}. {s}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='step-inactive'>{i}. {s}</div>", unsafe_allow_html=True)
        
        st.divider()
        st.info("💡 **Tip:** Adjustments are auto-saved. You can navigate back safely.")

def step_1_upload():
    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        st.subheader("1. Upload Data")
        st.write("Upload client P&L (Excel/CSV). The system will automatically detect year columns and line descriptions.")
        
        file = st.file_uploader("", type=['xlsx', 'csv'])
        if file:
            df = load_data_file(file)
            if not df.empty and len(df.columns) > 1:
                st.session_state.uploaded_df = df
                st.toast("File uploaded successfully!", icon="✅")
    
    with col_r:
        if "uploaded_df" in st.session_state:
            df = st.session_state.uploaded_df
            st.subheader("Data Preview")
            st.dataframe(df.head(8), use_container_width=True, height=300)
            
            st.markdown(f"**Detected Years:** {', '.join([c for c in df.columns if c != 'line item'])}")
            
            if st.button("Proceed to Business Model →"):
                st.session_state.step = 2
                st.rerun()

def step_2_model():
    st.subheader("2. Business Model & Accounting Policies")
    
    col_q, col_i = st.columns([2, 1])
    
    with col_q:
        st.markdown("##### Main Business Activities")
        
        # State-persistent radio buttons
        q1 = st.radio("Does the entity invest in financial assets as a main activity?", ["No", "Yes"], 
                      index=0 if st.session_state.get("q1_val") == "No" else 1, key="q1_val")
        
        q2 = st.radio("Does the entity provide financing to customers as a main activity?", ["No", "Yes"], 
                      index=0 if st.session_state.get("q2_val") == "No" else 1, key="q2_val")
        
        template = "General Corporate"
        if q1 == "Yes": template = "Investing Entity"
        if q2 == "Yes": template = "Financing Entity"
        st.session_state.template_key = template
        
        if template == "Financing Entity":
            st.markdown("---")
            st.markdown("##### Accounting Policy Choices")
            c1, c2 = st.columns(2)
            with c1:
                p1 = st.radio("Classify Cash & Equivalents?", ["Operating", "Investing"], key="pol_cash_radio")
                st.session_state.policy_cash = "Yes" if p1 == "Operating" else "No"
            with c2:
                p2 = st.radio("Classify Non-Customer Interest?", ["Operating", "Financing"], index=1, key="pol_fin_radio")
                st.session_state.policy_finance = "Yes" if p2 == "Operating" else "No"
    
    with col_i:
        st.info(f"**Selected Model:**\n\n### {template}")
        if template == "General Corporate":
            st.write("Standard classification. Operating expenses are bucketed by function.")
        elif template == "Investing Entity":
            st.write("Investment returns classified as Operating income.")
            
    st.divider()
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 1; st.rerun()
    if b2.button("Confirm & Continue →"): st.session_state.step = 3; st.rerun()

def step_3_map():
    st.subheader("3. Intelligent Mapping")
    st.write("Review auto-mapped lines. **Select 'Yes' in the Ungroup column** to split a line into detailed components.")

    df = st.session_state.uploaded_df
    g_lines, d_lines = get_ifrs18_data()
    target_options = g_lines + d_lines
    
    # Init Mapping once
    if "mapping_df" not in st.session_state:
        mapping = []
        for line in df["line item"]:
            best, _, _ = process.extractOne(str(line), target_options, scorer=fuzz.token_sort_ratio)
            mapping.append({"uploaded_line": line, "target_line": best, "Ungroup": "No"})
        st.session_state.mapping_df = pd.DataFrame(mapping)

    # Editor
    edited = st.data_editor(
        st.session_state.mapping_df,
        column_config={
            "uploaded_line": st.column_config.TextColumn("Source Line", disabled=True),
            "target_line": st.column_config.SelectboxColumn("IFRS 18 Target", options=target_options),
            "Ungroup": st.column_config.SelectboxColumn("Ungroup?", options=["No", "Yes"], width="small")
        },
        use_container_width=True,
        hide_index=True,
        height=500,
        key="map_editor" 
    )
    st.session_state.mapping_df = edited
    
    # Navigation
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 2; st.rerun()
    
    has_ungroup = any(edited["Ungroup"] == "Yes")
    lbl = "Proceed to Redistribution →" if has_ungroup else "Generate Final Report →"
    if b2.button(lbl):
        st.session_state.step = 4 if has_ungroup else 5
        st.rerun()

def step_4_redistribute():
    st.subheader("4. Granular Redistribution")
    st.info("Allocate grouped balances to specific IFRS 18 detailed accounts.")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    g_lines, d_lines = get_ifrs18_data()
    # Ungrouping targets usually detailed
    target_options = d_lines + g_lines
    year_cols = [c for c in df.columns if c != "line item"]
    
    ungroup_rows = mapping[mapping["Ungroup"] == "Yes"]
    if ungroup_rows.empty: st.session_state.step = 5; st.rerun()
    
    # We collect all allocations here
    alloc_list = []
    
    # Custom Tabs logic
    tabs = st.tabs([f"📄 {r['uploaded_line']}" for _, r in ungroup_rows.iterrows()])
    
    for i, tab in enumerate(tabs):
        with tab:
            row = ungroup_rows.iloc[i]
            src = row['uploaded_line']
            orig_vals = df[df["line item"] == src].iloc[0][year_cols]
            
            # Header with context
            c1, c2 = st.columns([1, 3])
            c1.markdown(f"**Source Line:** `{src}`")
            c1.markdown("**Total to Allocate:**")
            for y in year_cols:
                c1.metric(y, f"{orig_vals[y]:,.0f}")
            
            # Persistent Editor Key
            store_key = f"alloc_{src}_{i}"
            if store_key not in st.session_state:
                st.session_state[store_key] = pd.DataFrame([{"New IFRS Line": target_options[0], **{y: 0.0 for y in year_cols}}])
            
            with c2:
                edited = st.data_editor(
                    st.session_state[store_key],
                    column_config={"New IFRS Line": st.column_config.SelectboxColumn(options=target_options, width="large")},
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"widget_{store_key}"
                )
                st.session_state[store_key] = edited
                
                # Validation Logic
                diffs = orig_vals - edited[year_cols].sum()
                balanced = all(abs(d) < 1 for d in diffs)
                
                if balanced:
                    st.success("✅ Fully Allocated")
                else:
                    st.warning("⚠️ Unallocated Remainder:")
                    cols = st.columns(len(year_cols))
                    for idx, y in enumerate(year_cols):
                        cols[idx].metric(y, f"{diffs[y]:,.0f}", delta_color="inverse")
            
            # Save for final step
            temp = edited.copy()
            temp["_source"] = src
            alloc_list.append(temp)

    st.divider()
    b1, b2 = st.columns([1, 5])
    if b1.button("← Back"): st.session_state.step = 3; st.rerun()
    if b2.button("Finalize & Generate →"):
        st.session_state.final_alloc = pd.concat(alloc_list) if alloc_list else pd.DataFrame()
        st.session_state.step = 5
        st.rerun()

def step_5_report():
    st.subheader("5. Final IFRS 18 Presentation")
    
    df = st.session_state.uploaded_df
    mapping = st.session_state.mapping_df
    allocs = st.session_state.get("final_alloc", pd.DataFrame())
    year_cols = [c for c in df.columns if c != "line item"]
    template_key = st.session_state.template_key
    policies = {
        "cash_is_operating": st.session_state.get("policy_cash", "No"),
        "finance_is_operating": st.session_state.get("policy_finance", "No")
    }
    
    # --- Calc Engine ---
    g_lines, d_lines = get_ifrs18_data()
    all_lines = sorted(list(set(g_lines + d_lines)))
    final = pd.DataFrame({"line item": all_lines})
    final["Category"] = final["line item"].apply(lambda x: classify_category(x, template_key, policies))
    final = final.set_index("line item")
    for y in year_cols: final[y] = 0.0
    
    sankey_data = [] # For visualization
    
    # 1. Standard
    for _, m in mapping.iterrows():
        if m["Ungroup"] == "No":
            src, target = m["uploaded_line"], m["target_line"]
            vals = df[df["line item"] == src].iloc[0][year_cols]
            if target in final.index:
                for y in year_cols: final.at[target, y] += vals[y]
                # Log for Sankey (using first year for viz)
                val = vals[year_cols[0]]
                if abs(val) > 0:
                    cat = final.loc[target, "Category"]
                    sankey_data.append({"Source": src, "Target": cat, "Value": abs(val)})

    # 2. Allocations
    if not allocs.empty:
        for src, group in allocs.groupby("_source"):
            for _, r in group.iterrows():
                target = r["New IFRS Line"]
                if target in final.index:
                    for y in year_cols: final.at[target, y] += r[y]
                    # Log for Sankey
                    val = r[year_cols[0]]
                    if abs(val) > 0:
                        cat = final.loc[target, "Category"]
                        sankey_data.append({"Source": src, "Target": cat, "Value": abs(val)})
    
    # Display Logic
    final = final.reset_index()
    final = final[final[year_cols].abs().sum(axis=1) > 0.1]
    order = {"Operating": 1, "Investing": 2, "Financing": 3, "Income Tax": 4, "Discontinued Ops": 5}
    final["_order"] = final["Category"].map(order).fillna(99)
    final = final.sort_values(["_order", "line item"]).drop(columns=["_order"])
    
    # --- UI Components ---
    tab1, tab2 = st.tabs(["📄 Statement View", "📊 Visual Analysis"])
    
    with tab1:
        st.dataframe(
            final.style.format({y: "{:,.0f}" for y in year_cols})
                 .background_gradient(subset=year_cols, cmap="Reds", vmin=-100000, vmax=0)
                 .background_gradient(subset=year_cols, cmap="Greens", vmin=0, vmax=100000),
            use_container_width=True, height=600
        )
        csv = final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel/CSV", csv, "IFRS18_Final.csv", "text/csv")
        
    with tab2:
        if sankey_data:
            st.markdown("##### Source to Category Flow")
            sk_df = pd.DataFrame(sankey_data)
            # Aggregate for simpler chart
            sk_agg = sk_df.groupby(["Source", "Target"]).sum().reset_index()
            
            # Create Sankey using Plotly
            # Get unique labels
            labels = list(pd.concat([sk_agg["Source"], sk_agg["Target"]]).unique())
            label_map = {label: i for i, label in enumerate(labels)}
            
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15, thickness=20, line=dict(color="black", width=0.5),
                    label=labels, color="#D04A02"
                ),
                link=dict(
                    source=sk_agg["Source"].map(label_map),
                    target=sk_agg["Target"].map(label_map),
                    value=sk_agg["Value"]
                )
            )])
            fig.update_layout(title_text=f"Data Transformation Flow ({year_cols[0]})", font_size=10)
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
