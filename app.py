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
    # --- CHANGE START ---
    # Add state for handling manual mapping change confirmation
    if 'pending_mapping_change' not in st.session_state: st.session_state.pending_mapping_change = None
    # --- CHANGE END ---

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
    """
    Generates a complete HTML table string with custom PwC styling.
    Includes category headers, subtotals, and a grand total.
    """
    # Start the table and define the header
    html = '<table class="pwc-table"><thead><tr><th>Description</th>'
    for year in year_cols:
        html += f"<th>{year}</th>"
    html += '</tr></thead><tbody>'

    # Dictionary to store subtotals for the grand total calculation
    grand_totals = {year: 0 for year in year_cols}
    
    # Loop through each category to build the table body
    for category in category_order:
        category_df = df[df['Category'] == category]
        if not category_df.empty:
            # Add the category header row
            category_name = category.replace(" Category", "")
            html += f'<tr class="pwc-header"><td colspan="{len(year_cols) + 1}">{category_name}</td></tr>'

            # Add the data rows for the category
            for _, row in category_df.iterrows():
                html += f'<tr><td>{row["IFRS 18 Line Item"]}</td>'
                for year in year_cols:
                    value = row[year]
                    html += f'<td class="num-cell">{value:,.2f}</td>'
                html += '</tr>'

            # Calculate and add the subtotal row for the category
            subtotals = {year: category_df[year].sum() for year in year_cols}
            html += '<tr class="pwc-total"><td>Total</td>'
            for year in year_cols:
                subtotal_value = subtotals[year]
                # Only add to grand total if the category is not 'Discontinued Operations' or 'Other/Unclassified'
                if category not in ["Discontinued Operations Category", "Other/Unclassified"]:
                    grand_totals[year] += subtotal_value
                html += f'<td class="num-cell">{subtotal_value:,.2f}</td>'
            html += '</tr>'
    
    # Add the final grand total row
    html += '<tr class="pwc-grand"><td>Profit Before Tax and Discontinued Operations</td>'
    for year in year_cols:
        grand_total_value = grand_totals[year]
        html += f'<td class="num-cell">{grand_total_value:,.2f}</td>'
    html += '</tr>'
    
    # Close the table
    html += '</tbody></table>'
    return html

# --- CHANGE START: Function for confirmation dialog ---
@st.dialog("Confirm Change")
def confirm_mapping_change(change_info):
    """Shows a confirmation dialog for a mapping change."""
    st.write(f"Are you sure you want to change the classification from **'{change_info['old_val']}'** to **'{change_info['new_val']}'**?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Confirm Change", type="primary", use_container_width=True):
            # Apply the change
            df = st.session_state.mapping_df
            df.loc[change_info['index'], 'Suggested IFRS 18 Match'] = change_info['new_val']
            df.loc[change_info['index'], 'Confidence Score'] = 100
            st.session_state.mapping_df = df
            st.session_state.pending_mapping_change = None # Clear the pending change
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            # Discard the change
            st.session_state.pending_mapping_change = None # Clear the pending change
            st.rerun()
# --- CHANGE END ---


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
    with col1:
        if st.button("Provides financing to customers", use_container_width=True):
            st.session_state.entity_type, st.session_state.phase = "Provides financing to customers", "upload"; st.rerun()
    with col2:
        if st.button("Invests in financial assets", use_container_width=True):
            st.session_state.entity_type, st.session_state.phase = "Invests in financial assets", "upload"; st.rerun()
    with col3:
        if st.button("Other", use_container_width=True):
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
    
    # --- CHANGE START: Logic to handle confirmation dialog ---
    if st.session_state.pending_mapping_change:
        confirm_mapping_change(st.session_state.pending_mapping_change)
    # --- CHANGE END ---

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
    
    # --- CHANGE START: Detect edits to trigger confirmation ---
    # Store a copy of the dataframe before editing to detect changes
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

    # Compare the edited dataframe with the one from before the edit
    if not edited_df.equals(df_before_edit):
        # Find the exact change
        changed_rows = (edited_df != df_before_edit).any(axis=1)
        # Assuming only one change at a time from the UI
        if changed_rows.sum() == 1:
            changed_idx = changed_rows.idxmax()
            
            # Check if the change was in the 'Suggested IFRS 18 Match' column
            old_val = df_before_edit.loc[changed_idx, 'Suggested IFRS 18 Match']
            new_val = edited_df.loc[changed_idx, 'Suggested IFRS 18 Match']

            if old_val != new_val:
                st.session_state.pending_mapping_change = {
                    'index': changed_idx,
                    'old_val': old_val,
                    'new_val': new_val
                }
                st.rerun() # Rerun to launch the dialog
    # --- CHANGE END ---

    if st.button("Confirm Mapping", type="primary"):
        st.session_state.mapping_df = edited_df # Save the final state from the editor
        st.session_state.phase = "identify_ungroup"; st.rerun()


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
            st
