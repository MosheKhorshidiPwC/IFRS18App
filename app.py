# app.py

import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import time
import re
import config # Import the new configuration file

# --- Page Configuration ---
st.set_page_config(
    page_title="IFRS 18 Transformation Tool",
    page_icon="logo_PwC.png",
    layout="wide"
)

# --- Helper Functions ---
def local_css(file_name):
    """Loads a local CSS file into the Streamlit app."""
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file '{file_name}' not found. Please ensure it's in the same directory.")

def initialize_session_state():
    """Initializes all necessary session state variables."""
    if 'phase' not in st.session_state: st.session_state.phase = "entity_select"
    if 'original_df' not in st.session_state: st.session_state.original_df = None
    if 'mapping_df' not in st.session_state: st.session_state.mapping_df = None
    if 'ungroup_choices' not in st.session_state: st.session_state.ungroup_choices = {}
    if 'allocation_values' not in st.session_state: st.session_state.allocation_values = {}
    if 'pending_mapping_change' not in st.session_state: st.session_state.pending_mapping_change = None

def custom_scorer(s1, s2):
    """Custom fuzzy matching scorer to improve accuracy."""
    s1_lower, s2_lower = s1.lower(), s2.lower()
    base_score = fuzz.WRatio(s1, s2)
    if 'revenue' in s1_lower and 'cost' not in s1_lower and 'cost' in s2_lower and 'revenue' in s2_lower: base_score -= 30
    if 'income' in s1_lower and 'expense' not in s1_lower and 'expense' in s2_lower: base_score -= 20
    if 'expense' in s1_lower and 'income' not in s1_lower and 'income' in s2_lower: base_score -= 20
    if 'r&d' in s1_lower and 'research and development' in s2_lower: base_score += 20
    if 'g&a' in s1_lower and 'general and administrative' in s2_lower: base_score += 20
    return max(0, base_score)

def render_header():
    """Renders the main header with the PwC logo."""
    pad,col1, col2 = st.columns([0.1,0.4, 5]) 
    with pad:
        st.header(" ")
    with col1:
        st.image("logo_PwC.png", width=100) 
    with col2:
        st.markdown("<h1 style='margin-top: -18px;'>IFRS 18 P&L Transformation Tool</h1>", unsafe_allow_html=True)
    st.markdown("---")

def generate_final_report_html(df, year_cols, category_order):
    """Generates a complete HTML table string with custom PwC styling."""
    html = '<table class="pwc-table"><thead><tr><th>Description</th>'
    for year in year_cols:
        html += f"<th>{year}</th>"
    html += '</tr></thead><tbody>'
    grand_totals = {year: 0 for year in year_cols}
    for category in category_order:
        category_df = df[df['Category'] == category]
        if not category_df.empty:
            category_name = category.replace(" Category", "")
            html += f'<tr class="pwc-header"><td colspan="{len(year_cols) + 1}">{category_name}</td></tr>'
            for _, row in category_df.iterrows():
                html += f'<tr><td>{row["IFRS 18 Line Item"]}</td>'
                for year in year_cols:
                    value = row[year]
                    html += f'<td class="num-cell">{value:,.2f}</td>'
                html += '</tr>'
            subtotals = {year: category_df[year].sum() for year in year_cols}
            html += '<tr class="pwc-total"><td>Total</td>'
            for year in year_cols:
                subtotal_value = subtotals[year]
                if category not in ["Discontinued Operations Category", "Other/Unclassified"]:
                    grand_totals[year] += subtotal_value
                html += f'<td class="num-cell">{subtotal_value:,.2f}</td>'
            html += '</tr>'
    html += '<tr class="pwc-grand"><td>Profit Before Tax and Discontinued Operations</td>'
    for year in year_cols:
        grand_total_value = grand_totals[year]
        html += f'<td class="num-cell">{grand_total_value:,.2f}</td>'
    html += '</tr>'
    html += '</tbody></table>'
    return html

@st.dialog("Confirm Change")
def confirm_mapping_change(change_info):
    """Shows a confirmation dialog and updates confidence to 100% on confirmation."""
    st.write(f"Are you sure you want to change the classification from **'{change_info['old_val']}'** to **'{change_info['new_val']}'**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Confirm Change", type="primary", use_container_width=True):
            df = st.session_state.mapping_df
            df.loc[change_info['index'], 'Suggested IFRS 18 Match'] = change_info['new_val']
            # Set security level to 100% upon manual change
            df.loc[change_info['index'], 'Confidence Score'] = 100 
            st.session_state.mapping_df = df
            st.session_state.pending_mapping_change = None
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pending_mapping_change = None
            st.rerun()

# --- Main Application Logic ---
initialize_session_state()
local_css("style.css")
render_header()

# --- Phase 1: Select Entity Type ---
if st.session_state.phase == "entity_select":
    st.header("")
    st.markdown("<h2 style='text-align: center; font-weight: bold;'>What is your entity's main business activity?</h2>", unsafe_allow_html=True)
    st.write("") 
    col1, col2, col3 = st.columns(3)
    if col1.button("Provides financing to customers", use_container_width=True):
        st.session_state.entity_type, st.session_state.phase = "Provides financing to customers", "upload"; st.rerun()
    if col2.button("Invests in financial assets", use_container_width=True):
        st.session_state.entity_type, st.session_state.phase = "Invests in financial assets", "upload"; st.rerun()
    if col3.button("Other", use_container_width=True):
        st.session_state.entity_type, st.session_state.phase = "Other", "upload"; st.rerun()

# --- Phase 2: Data Upload ---
if st.session_state.phase == "upload":
    st.header("Upload Your P&L Statement")
    uploaded_file = st.file_uploader("Upload your Excel file.", type=['xlsx'])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, header=0) 
            if df.shape[1] < 4: 
                st.error("The uploaded file has fewer than 4 columns. Please upload a file with at least a description column and three years of data.")
            else:
                df = df.iloc[:, :4]
                st.session_state.original_df, st.session_state.phase = df, "mapping"; st.rerun()
        except Exception as e: 
            st.error(f"An error occurred while reading the file: {e}")

# --- Phase 3: Line Item Mapping ---
if st.session_state.phase == "mapping":
    st.header("Map Your Line Items to IFRS 18")
    st.write("Review our suggested matches and correct them as needed.")
    
    if st.session_state.pending_mapping_change:
        confirm_mapping_change(st.session_state.pending_mapping_change)

    if 'mapping_df' not in st.session_state or st.session_state.mapping_df is None:
        mapping_data = []
        df = st.session_state.original_df
        line_item_col = df.columns[0] 
        for item in df[line_item_col]:
            item_str = str(item)
            item_lower = item_str.lower().strip()
            if any(keyword in item_lower for keyword in config.EXCLUSION_KEYWORDS): 
                match, score = config.SUBTOTAL_MAPPING_VALUE, 95
            elif item_lower in config.ABBREVIATION_MAP: 
                match, score = config.ABBREVIATION_MAP[item_lower], 100
            else: 
                match, score = process.extractOne(item_str, config.IFRS_18_MASTER_LIST, scorer=custom_scorer)
            mapping_data.append({line_item_col: item, "Suggested IFRS 18 Match": match, "Confidence Score": int(score)})
        st.session_state.mapping_df = pd.DataFrame(mapping_data)

    mapping_options = [config.SUBTOTAL_MAPPING_VALUE] + sorted(config.IFRS_18_MASTER_LIST)
    line_item_col = st.session_state.original_df.columns[0]
    
    df_before_edit = st.session_state.mapping_df.copy()
    edited_df = st.data_editor(st.session_state.mapping_df, 
                               column_config={
                                   line_item_col: st.column_config.TextColumn("Original Line Item", disabled=True), 
                                   "Suggested IFRS 18 Match": st.column_config.SelectboxColumn(options=mapping_options, required=True), 
                                   "Confidence Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")
                               }, 
                               hide_index=True, 
                               use_container_width=True,
                               key="mapping_editor")

    if not edited_df.equals(df_before_edit):
        changed_rows = (edited_df != df_before_edit).any(axis=1)
        if changed_rows.sum() == 1:
            changed_idx = changed_rows.idxmax()
            old_val = df_before_edit.loc[changed_idx, 'Suggested IFRS 18 Match']
            new_val = edited_df.loc[changed_idx, 'Suggested IFRS 18 Match']
            if old_val != new_val:
                st.session_state.pending_mapping_change = {'index': changed_idx, 'old_val': old_val, 'new_val': new_val}
                st.rerun()

    if st.button("Confirm Mapping", type="primary"):
        st.session_state.mapping_df = edited_df
        st.session_state.phase = "identify_ungroup"
        st.rerun()

# --- Phase 4: Identify, Ungroup & Classify ---
if st.session_state.phase == "identify_ungroup":
    st.header("")
    st.subheader("For each IFRS 18 item below, is it currently grouped within your existing statement?")
    
    line_item_col = st.session_state.original_df.columns[0]
    mapped_items = st.session_state.mapping_df[st.session_state.mapping_df['Suggested IFRS 18 Match'] != config.SUBTOTAL_MAPPING_VALUE].dropna(subset=['Suggested IFRS 18 Match'])
    used_items = set(mapped_items['Suggested IFRS 18 Match'])
    missing_items = sorted(list(set(config.IFRS_18_MASTER_LIST) - used_items))
    entity_type_key = st.session_state.entity_type
    applicable_missing_items = [item for item in missing_items if (item not in config.ENTITY_DEPENDENT_ITEMS) or (config.ENTITY_DEPENDENT_ITEMS[item].get(entity_type_key) != "N/A")]
    parent_list = config.PARENT_LIST_A if entity_type_key != 'Invests in financial assets' else config.PARENT_LIST_B
    valid_parents_mapped = mapped_items[mapped_items['Suggested IFRS 18 Match'].isin(parent_list)]
    valid_parent_options = list(valid_parents_mapped[line_item_col])
    if not st.session_state.ungroup_choices: 
        st.session_state.ungroup_choices = {item: {} for item in applicable_missing_items}
    
    with st.container():
        st.markdown('<div class="ungroup-container">', unsafe_allow_html=True)
        for i, item in enumerate(applicable_missing_items):
            st.markdown("---")
            st.markdown(f'<div class="fade-in-row" style="animation-delay: {i*0.05}s;">', unsafe_allow_html=True)
            cols = st.columns([2.5, 1, 2, 2])
            with cols[0]: st.write(f"**{item}**")
            with cols[1]: st.session_state.ungroup_choices[item]['is_grouped'] = st.radio(" ", ["No", "Yes"], key=f"grouped_{item}", horizontal=True, label_visibility="collapsed")
            if st.session_state.ungroup_choices[item].get('is_grouped') == 'Yes':
                with cols[2]: st.session_state.ungroup_choices[item]['parent'] = st.selectbox("Parent", valid_parent_options, key=f"parent_{item}", index=None, placeholder="Select...", label_visibility="collapsed")
                if item in config.SPECIAL_POLICY_ITEMS and entity_type_key in config.SPECIAL_POLICY_ITEMS[item]:
                    with cols[3]: st.session_state.ungroup_choices[item]['policy_choice'] = st.selectbox("Classify", config.SPECIAL_POLICY_ITEMS[item][entity_type_key], key=f"policy_{item}", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("""
        <style> .floating-button-container { position: fixed; bottom: 40px; right: 40px; z-index: 1000; } </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="floating-button-container">', unsafe_allow_html=True)
    if st.button("Proceed to Allocation", type="primary"):
        st.session_state.phase = "allocation"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- Phase 5: Value Allocation ---
if st.session_state.phase == "allocation":
    st.header("Allocate Values")
    st.write("Allocate values for the new line items. Any remaining amount will stay with the parent account.")
    
    items_to_allocate = {}
    for item, choices in st.session_state.ungroup_choices.items():
        if choices.get('is_grouped') == 'Yes' and choices.get('parent'):
            parent = choices['parent']
            if parent not in items_to_allocate: 
                items_to_allocate[parent] = []
            items_to_allocate[parent].append(item)
            
    if not items_to_allocate: 
        st.info("No items selected for allocation. Proceed to generate the report.")
    else:
        original_df = st.session_state.original_df
        line_item_col = original_df.columns[0]
        year_cols = list(original_df.columns[1:])
        
        for parent_name, new_items in items_to_allocate.items():
            with st.expander(f"Allocate from: **{parent_name}**", expanded=True):
                parent_row = original_df[original_df[line_item_col] == parent_name].iloc[0]
                if parent_name not in st.session_state.allocation_values: 
                    st.session_state.allocation_values[parent_name] = {item: {y: 0.0 for y in year_cols} for item in new_items}
                
                cols = st.columns(len(year_cols))
                for i, year in enumerate(year_cols):
                    with cols[i]:
                        st.subheader(year)
                        st.metric("Original Total", f"{parent_row[year]:,.2f}")
                        total_allocated = 0
                        for new_item in new_items:
                            allocated_val = st.number_input(f"To: {new_item}", 
                                                            key=f"alloc_{parent_name}_{new_item}_{year}", 
                                                            value=st.session_state.allocation_values[parent_name][new_item].get(year, 0.0), 
                                                            step=1000.0, format="%.2f")
                            st.session_state.allocation_values[parent_name][new_item][year] = allocated_val
                            total_allocated += allocated_val
                        remaining = parent_row[year] - total_allocated
                        st.metric("Amount Allocated", f"{total_allocated:,.2f}")
                        st.metric("Remaining in Parent", f"{remaining:,.2f}", delta_color="off")
                        
    if st.button("Generate New P&L", type="primary"): 
        st.session_state.phase = "final_report"
        st.rerun()

# --- Phase 6: Final Report (Using Custom HTML) ---
if st.session_state.phase == "final_report":
    st.header("IFRS 18 P&L Statement")
    with st.spinner("Generating your new P&L statement..."):
        line_item_col = st.session_state.original_df.columns[0]
        year_cols = list(st.session_state.original_df.columns[1:])
        final_df = pd.merge(st.session_state.mapping_df, st.session_state.original_df, on=line_item_col)
        final_df = final_df.rename(columns={'Suggested IFRS 18 Match': 'IFRS 18 Line Item', line_item_col: 'Original Line Item'})
        new_rows = []
        for parent_name, new_items_alloc in st.session_state.allocation_values.items():
            parent_idx = final_df[final_df['Original Line Item'] == parent_name].index
            for new_item_name, year_vals in new_items_alloc.items():
                year_dict = {year: year_vals.get(year, 0.0) for year in year_cols}
                for year, val in year_dict.items(): 
                    if not parent_idx.empty:
                        final_df.loc[parent_idx, year] -= val
                new_rows.append({'Original Line Item': f"{new_item_name} (Ungrouped)", 'IFRS 18 Line Item': new_item_name, **year_dict})
        if new_rows: 
            final_df = pd.concat([final_df, pd.DataFrame(new_rows)], ignore_index=True)
        final_df['Category'] = 'Unmapped / Subtotal'
        mappable_rows = (final_df['IFRS 18 Line Item'].notna()) & (final_df['IFRS 18 Line Item'] != config.SUBTOTAL_MAPPING_VALUE)
        
        def get_classification(row):
            item_name, entity_type = row['IFRS 18 Line Item'], st.session_state.entity_type
            if item_name in st.session_state.ungroup_choices and 'policy_choice' in st.session_state.ungroup_choices[item_name]: 
                return st.session_state.ungroup_choices[item_name]['policy_choice']
            if item_name in config.FIXED_OPERATING_ITEMS: return "Operating Category"
            if item_name in config.FIXED_FINANCING_ITEMS: return "Financing Category"
            if item_name in config.FIXED_INVESTING_ITEMS: return "Investing Category"
            if item_name in config.FIXED_TAX_ITEMS: return "Income Taxes Category"
            if item_name in config.FIXED_DISCONTINUED_ITEMS: return "Discontinued Operations Category"
            if item_name in config.ENTITY_DEPENDENT_ITEMS:
                classification = config.ENTITY_DEPENDENT_ITEMS[item_name].get(entity_type)
                if classification and classification not in ['N/A', 'Accounting Policy']: 
                    return classification
            return "Other/Unclassified"
            
        final_df.loc[mappable_rows, 'Category'] = final_df[mappable_rows].apply(get_classification, axis=1)
        category_order = ["Operating Category", "Investing Category", "Financing Category", "Income Taxes Category", "Discontinued Operations Category", "Other/Unclassified"]
        final_df['Category'] = pd.Categorical(final_df['Category'], categories=category_order + ["Unmapped / Subtotal"], ordered=True)
        final_df = final_df.sort_values('Category')
        display_df = final_df[(final_df['IFRS 18 Line Item'].notna()) & (final_df['IFRS 18 Line Item'] != config.SUBTOTAL_MAPPING_VALUE)].copy()

        st.markdown("---")
        report_html = generate_final_report_html(display_df, year_cols, category_order)
        st.markdown(report_html, unsafe_allow_html=True)
        st.write("") 

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')
            
        csv = convert_df_to_csv(display_df)
        st.download_button(label="Download P&L as CSV", data=csv, file_name="ifrs18_transformed_pnl.csv", mime="text/csv", key="final_report_download")
