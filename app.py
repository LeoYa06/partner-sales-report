import streamlit as st
import pandas as pd
import datetime
import io
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
    
    # Check if we received a list of DataFrames or a single one
    if isinstance(df_combined, list):
        dfs_to_process = df_combined
    else:
        dfs_to_process = [df_combined]

    for df in dfs_to_process:
        data = [df.columns.to_list()] + df.values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

    if metrics:
        for label, val in metrics.items():
            elements.append(Paragraph(f"<b>{label}:</b> {val}", styles['Normal']))
            
    doc.build(elements)
    return buffer.getvalue()

def export_partner_csv(df_combined, header_info, metrics):
    output = io.StringIO()
    output.write(f",,,,Invoice Number,{header_info['invoice']}\n")
    output.write(f",Week Sales From,,{header_info['start']}\n")
    output.write(f",,thru,{header_info['end']}\n\n")
    df_combined.to_csv(output, index=False)
    output.write("\nTAXES AND COMMISSIONS\n")
    for label, val in metrics.items():
        output.write(f"{label},{val}\n")
    return output.getvalue().encode('utf-8')

# --- STREAMLIT INTERFACE ---
st.title("🚀 Sales Automation System")
uploaded_file = st.file_uploader("Upload 'Item Sales' file (CSV)", type="csv")

if uploaded_file:
    report_dt, report_day = get_report_info(uploaded_file)
    date_str = report_dt.strftime('%Y-%m-%d')
    start_w, end_w = get_week_range(report_dt)
    # --- CARGA Y LIMPIEZA DE DATOS ---
    df_sales = pd.read_csv(uploaded_file, skiprows=6).fillna('')

    # Esta función quita las comas de los números (ej: "3,473" -> 3473)
    def clean_numeric_column(val):
        if isinstance(val, str):
            val = val.replace(',', '').strip()
            return int(val) if val.isdigit() else 0
        return int(val)

    # Aplicamos la limpieza a la columna Count antes de procesarla
    df_sales['Count'] = df_sales['Count'].apply(clean_numeric_column)

    # --- RAW DATA EXPANDER ---
    with st.expander("View Filtered Raw Data"):
        st.dataframe(df_sales[['Item', 'Count', 'Pre-tax Total']], use_container_width=True)

    # --- 1. STATION TRACKER ---
    st.header("1. General Station Tracker")
    daily_counts = {stn: 0 for stn in STATIONS_GENERAL}
    for _, row in df_sales.iterrows():
        tags = [t.strip() for t in str(row['Tags']).split(',')]
        for tag in tags:
            if tag in TAG_MAPPING_GENERAL:
                name = TAG_MAPPING_GENERAL[tag]
                if name in daily_counts: daily_counts[name] += row['Count']
                break
    
    tracker_data = []
    for stn in STATIONS_GENERAL:
        row_data = {'Station': stn}
        # Initialize all days in 0
        for d in DAYS_NAME:
            row_data[d] = 0
        # Fill only the report day
        if report_day in DAYS_NAME:
            row_data[report_day] = daily_counts[stn]
        row_data['Weekly Total'] = daily_counts[stn]
        tracker_data.append(row_data)
    
    df_tracker = pd.DataFrame(tracker_data)
    st.dataframe(df_tracker, use_container_width=True)

    # Tracker PDF Button (Corrected line)
    pdf_tracker = export_partner_pdf(df_tracker, {"invoice": "N/A", "start": date_str, "end": date_str}, {}, "General Station Tracker")
    st.download_button("🖨️ Print Station Tracker (PDF)", data=pdf_tracker, file_name=f"Tracker_{date_str}.pdf")

    # --- 2. PARTNER EXTRACT ---
    st.write("---")
    st.header("2. Partner Extract (Original Format)")
    
    partner_query = st.text_input("Search Partner or Tag (e.g., dock-local, sushi)", value="dock-local").lower()
    
    if partner_query:
        partner_sales = 0.0
        item_details = []
        for _, row in df_sales.iterrows():
            tags = [t.strip().lower() for t in str(row['Tags']).split(',')]
            if any(partner_query in t for t in tags):
                val = clean_money(row['Pre-tax Total'])
                partner_sales += val
                item_details.append({'Item': row['Item'], 'Count': row['Count']})

        if item_details:
            df_items = pd.DataFrame(item_details).groupby('Item')['Count'].sum().reset_index()
            rows_combined = []
            invoice_num = f"{partner_query.replace('-','').upper()}{report_dt.strftime('%m%d%y')}"
            
            for i, day_name in enumerate(DAYS_NAME):
                current_date = start_w + datetime.timedelta(days=i)
                is_report_day = current_date.date() == report_dt.date()
                daily_val = partner_sales if is_report_day else 0.0
                item_n = df_items.iloc[i]['Item'] if i < len(df_items) else ""
                item_c = df_items.iloc[i]['Count'] if i < len(df_items) else ""
                
                rows_combined.append({
                    'Date': current_date.strftime('%Y-%m-%d'),
                    'Day': day_name,
                    'Main St': f"{daily_val:,.2f}" if daily_val > 0 else "0",
                    'Cash': "0",
                    'Total Net Sales': f"{daily_val:,.2f}" if daily_val > 0 else "0",
                    'Item Detail': item_n,
                    'Total Count': item_c
                })
            
            if len(df_items) > 7:
                for i in range(7, len(df_items)):
                    rows_combined.append({'Date': '', 'Day': '', 'Main St': '', 'Cash': '', 'Total Net Sales': '', 'Item Detail': df_items.iloc[i]['Item'], 'Total Count': df_items.iloc[i]['Count']})

            df_combined = pd.DataFrame(rows_combined)
            h_info = {'invoice': invoice_num, 'start': start_w.strftime('%Y-%m-%d'), 'end': end_w.strftime('%Y-%m-%d')}
            
            st.info(f"**Invoice:** {h_info['invoice']} | **Period:** {h_info['start']} to {h_info['end']}")
            st.table(df_combined)
            
            st.subheader("Totals and Commissions")
            tax_val = partner_sales * 0.0825
            partner_com = partner_sales * 0.80
            aramark_com = partner_sales * 0.20
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Net Sales", f"${partner_sales:,.2f}")
            m2.metric("Tax (8.25%)", f"${tax_val:,.2f}")
            m3.metric("Partner (80%)", f"${partner_com:,.2f}")
            m4.metric("Aramark (20%)", f"${aramark_com:,.2f}")

            metrics_dict = {
                "Total Net Sales": f"${partner_sales:,.2f}",
                "Tax (8.25%)": f"${tax_val:,.2f}",
                "Partner Share (80%)": f"${partner_com:,.2f}",
                "Aramark Share (20%)": f"${aramark_com:,.2f}"
            }
            
            st.write("### Report Actions")
            c1, c2 = st.columns(2)
            with c1:
                # Passing single DataFrame here works now
                pdf_bytes = export_partner_pdf(df_combined, h_info, metrics_dict, f"{partner_query.upper()} Partner Report")
                st.download_button("🖨️ Print PDF Report", data=pdf_bytes, file_name=f"Report_{partner_query}_{date_str}.pdf")
            with c2:
                csv_bytes = export_partner_csv(df_combined, h_info, metrics_dict)
                st.download_button("📥 Download CSV Tracker", data=csv_bytes, file_name=f"Tracker_{partner_query}_{date_str}.csv")
        else:
            st.warning("No data found for this partner.")
            