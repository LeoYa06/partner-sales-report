import pandas as pd
import datetime
import io
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- CONFIGURATION & MAPPINGS ---
st.set_page_config(page_title="Sales Automation System", layout="wide")

TAG_MAPPING_GENERAL = {
    'far-east-mto': 'Far East Made to Order',
    'far-east-express-tracker': 'Far Easet Express',
    'far-east-protein-only': 'Far East Protein Only',
    'far-east-shrimp': 'Far East Shrimp Entrée',
    'far-east-side-tracker': 'Far East Side/Extra Protein/Shrimp/Egg Rolls',
    'far-east-egg-roll': 'Far East Side/Extra Protein/Shrimp/Egg Rolls',
    'elevated-table-tracker': 'Elevated Table Entrée',
    'elevated-table-protein-tracker': 'Elevated Table Protein Only',
    'modern-greens-tracker': 'Modern Greens',
    'soup-tracker': 'Modern Greens Soup',
    'market-bar-tracker': 'Market Bar',
    'hopes-cookie-tracker': 'Hopes Cookies',
    'sushi-tracker': 'Far East Sushi',
    'dock-local-special': 'Dock Local Special',
    'dock-local-3-taco-lobster': '3Taco/Lobster',
    'dock-local-bowl-2-taco': '2Taco/Bowl',
    'dock-local-lobster': 'Lobster Roll Combo',
    'dock-local-side': 'Side',
    'dock-local-protein': 'Protein'
}

STATIONS_GENERAL = [
    'Far East Made to Order', 'Far Easet Express', 'Far East Protein Only', 
    'Far East Shrimp Entrée', 'Far East Side/Extra Protein/Shrimp/Egg Rolls',
    'Elevated Table Entrée', 'Elevated Table Protein Only', 'Elevated Table Side Only',
    'Modern Greens', 'Modern Greens Soup', 'Market Bar', 'Hopes Cookies', 
    'Far East Sushi', 'Dock Local Special', '3Taco/Lobster', '2Taco/Bowl', 
    'Lobster Roll Combo', 'Side', 'Protein'
]

DAYS_NAME = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']

# --- SUPPORT FUNCTIONS ---
def clean_money(val):
    if isinstance(val, str):
        return float(val.replace('$', '').replace(',', ''))
    return val

def get_report_info(uploaded_file):
    uploaded_file.seek(0)
    lines = uploaded_file.getvalue().decode('utf-8').splitlines()
    for line in lines:
        if "Report start time" in line:
            date_str = line.split(',')[1].strip().strip('"').split(' ')[0]
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            return dt, dt.strftime('%A')
    return None, None

def get_week_range(report_dt):
    offset = (report_dt.weekday() - 3) % 7
    start_week = report_dt - datetime.timedelta(days=offset)
    end_week = start_week + datetime.timedelta(days=6)
    return start_week, end_week

# --- EXPORT GENERATORS ---
def export_partner_pdf(df_combined, header_info, metrics, title):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    # Header Info
    elements.append(Paragraph(f"<b>Invoice Number:</b> {header_info.get('invoice', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Week Sales From:</b> {header_info.get('start', '')} <b>thru</b> {header_info.get('end', '')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(title, styles['Title']))
    
    if isinstance(df_combined, list):
        dfs_to_process = df_combined