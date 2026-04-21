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

# Mappings Plano 2
TAG_MAPPING_P2 = {
    'far-east-mto': 'Far East Made to Order',
    'far-east-express-tracker': 'Far East Express',
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
    'oda': 'Oda', 'halal': 'Halal', 'a2b': 'A2B', 'lucis': 'Lucis'
}

STATIONS_P2 = [
    'Far East Made to Order', 'Far East Express', 'Far East Protein Only', 
    'Far East Shrimp Entrée', 'Far East Side/Extra Protein/Shrimp/Egg Rolls',
    'Elevated Table Entrée', 'Elevated Table Protein Only', 'Modern Greens', 
    'Modern Greens Soup', 'Market Bar', 'Hopes Cookies', 'Far East Sushi',
    'Oda', 'Halal', 'A2B', 'Lucis'
]

# Mappings Plano 1
STATIONS_P1 = ["Uno Mas", "Salad Bar", "Fiamma", "Salt & Sesame", "Oda", "Halal", "A2B", "Sushi"]
MAPPING_P1 = {
    "unomas": "Uno Mas", "unomas-station-tracker": "Uno Mas",
    "heirloom": "Salad Bar", "salad-bar-station-tracker": "Salad Bar",
    "fiamma": "Fiamma", "fiamma-entree-station-tracker": "Fiamma",
    "salt-sesame-station-tracker": "Salt & Sesame",
    "oda": "Oda", "halal": "Halal", "a2b": "A2B", "sushi-tracker": "Sushi"
}

DAYS_NAME = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']

# --- SIDEBAR: SELECCIÓN DE UBICACIÓN ---
st.sidebar.title("📍 Ubicación")
location = st.sidebar.selectbox("Seleccione Local", ["JPMC Plano 2", "JPMC Plano 1"])

if location == "JPMC Plano 1":
    current_stations = STATIONS_P1
    current_mapping = MAPPING_P1
    COMMISSION_RATES = {"ODA": 0.25, "A2B": 0.25, "SUSHI": 0.25, "HALAL": 0.20, "UNO": 0.20, "FIAMMA": 0.20}
else:
    current_stations = STATIONS_P2
    current_mapping = TAG_MAPPING_P2
    COMMISSION_RATES = {"DOCK": 0.20, "ODA": 0.25, "HALAL": 0.20, "A2B": 0.25, "LUCIS": 0.20, "SUSHI": 0.25}

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

def export_partner_pdf(df_combined, header_info, metrics, title):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>Invoice Number:</b> {header_info.get('invoice', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Week Sales From:</b> {header_info.get('start', '')} <b>thru</b> {header_info.get('end', '')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(title, styles['Title']))
    
    data = [df_combined.columns.to_list()] + df_combined.values.tolist()
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
    output.write(f",,,Invoice Number,{header_info['invoice']}\n")
    output.write(f",Week Sales From,,{header_info['start']}\n")
    output.write(f",,thru,{header_info['end']}\n\n")
    df_combined.to_csv(output, index=False)
    output.write("\nTAXES AND COMMISSIONS\n")
    for label, val in metrics.items():
        output.write(f"{label},{val}\n")
    return output.getvalue().encode('utf-8')

# --- INITIALIZE MEMORY ---
if 'weekly_accumulator' not in st.session_state:
    st.session_state.weekly_accumulator = []

# --- STREAMLIT INTERFACE ---
st.title(f"🚀 Sales Automation System - {location}")
uploaded_file = st.file_uploader("Upload 'Item Sales' file (CSV)", type="csv")

if uploaded_file:
    report_dt, report_day = get_report_info(uploaded_file)
    date_str = report_dt.strftime('%m-%d-%Y')
    start_w, end_w = get_week_range(report_dt)
    
    df_sales = pd.read_csv(uploaded_file, skiprows=6).fillna('')

    def clean_numeric_column(val):
        if isinstance(val, str):
            val = val.replace(',', '').strip()
            return int(val) if val.isdigit() else 0
        return int(val)

    df_sales['Count'] = df_sales['Count'].apply(clean_numeric_column)

    with st.expander("View Filtered Raw Data"):
        st.dataframe(df_sales[['Item', 'Count', 'Pre-tax Total']], use_container_width=True)

    # --- 1. STATION TRACKER ---
    st.header("1. General Station Tracker")
    daily_counts = {stn: 0 for stn in current_stations}
    for _, row in df_sales.iterrows():
        tags = [t.strip() for t in str(row['Tags']).split(',')]
        for tag in tags:
            if tag in current_mapping:
                name = current_mapping[tag]
                if name in daily_counts: daily_counts[name] += row['Count']
                break
    
    tracker_data = []
    for stn in current_stations:
        row_data = {'Station': stn}
        for d in DAYS_NAME: row_data[d] = 0
        if report_day in DAYS_NAME: row_data[report_day] = daily_counts[stn]
        row_data['Weekly Total'] = daily_counts[stn]
        tracker_data.append(row_data)
    
    df_tracker = pd.DataFrame(tracker_data)
    st.dataframe(df_tracker, use_container_width=True)

    # --- 2. PARTNER EXTRACT ---
    st.write("---")
    st.header("2. Partner Extract")
    partner_query = st.text_input("Search Partner (e.g., oda, unomas, sushi):").lower()
    
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
            
            # --- LÓGICA INVOICE & FECHAS ---
            prefijo = partner_query.replace('-', ' ').split()[0].upper()
            fecha_invoice = end_w.strftime('%d%m%y')
            invoice_num = f"{prefijo}{fecha_invoice}"
            
            rows_combined = []
            for i, day_name in enumerate(DAYS_NAME):
                current_date = start_w + datetime.timedelta(days=i)
                is_report_day = current_date.date() == report_dt.date()
                daily_val = partner_sales if is_report_day else 0.0
                item_n = df_items.iloc[i]['Item'] if i < len(df_items) else ""
                item_c = df_items.iloc[i]['Count'] if i < len(df_items) else ""
                
                rows_combined.append({
                    'Date': current_date.strftime('%m-%d-%Y'),
                    'Day': day_name,
                    'Main St': f"{daily_val:,.2f}" if daily_val > 0 else "0",
                    'Total Net Sales': f"{daily_val:,.2f}" if daily_val > 0 else "0",
                    'Item Detail': item_n,
                    'Total Count': item_c
                })

            if len(df_items) > 7:
                for i in range(7, len(df_items)):
                    rows_combined.append({'Date': '', 'Day': '', 'Main St': '', 'Total Net Sales': '', 'Item Detail': df_items.iloc[i]['Item'], 'Total Count': df_items.iloc[i]['Count']})

            df_combined = pd.DataFrame(rows_combined)
            h_info = {'invoice': invoice_num, 'start': start_w.strftime('%m-%d-%Y'), 'end': end_w.strftime('%m-%d-%Y')}
            
            st.info(f"**Invoice:** {h_info['invoice']} | **Period:** {h_info['start']} to {h_info['end']}")
            st.table(df_combined)

            # --- COMISIONES ---
            aramark_rate = COMMISSION_RATES.get(prefijo, 0.20)
            partner_rate = 1.0 - aramark_rate
            tax_val = partner_sales * 0.0825
            partner_com = partner_sales * partner_rate
            aramark_com = partner_sales * aramark_rate
            total_pay_val = tax_val + partner_com
            pay_label = f"{prefijo.capitalize()} Pay"

            st.subheader("Totals and Commissions")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Net Sales", f"${partner_sales:,.2f}")
            m2.metric("Tax (8.25%)", f"${tax_val:,.2f}")
            m3.metric(f"Partner ({partner_rate*100:.0f}%)", f"${partner_com:,.2f}")
            m4.metric(f"Aramark ({aramark_rate*100:.0f}%)", f"${aramark_com:,.2f}")

            st.markdown("---")
            st.metric(label=f"💰 {pay_label}", value=f"${total_pay_val:,.2f}")

            metrics_dict = {
                "Total Net Sales": f"${partner_sales:,.2f}",
                "Tax (8.25%)": f"${tax_val:,.2f}",
                f"Partner Share ({partner_rate*100:.0f}%)": f"${partner_com:,.2f}",
                f"Aramark Share ({aramark_rate*100:.0f}%)": f"${aramark_com:,.2f}",
                pay_label: f"${total_pay_val:,.2f}"
            }
            
            st.write("### Actions")
            c1, c2 = st.columns(2)
            with c1:
                pdf_bytes = export_partner_pdf(df_combined, h_info, metrics_dict, f"{prefijo} Partner Report")
                st.download_button("🖨️ Print PDF", data=pdf_bytes, file_name=f"Report_{prefijo}_{date_str}.pdf")
            with c2:
                csv_bytes = export_partner_csv(df_combined, h_info, metrics_dict)
                st.download_button("📥 Download CSV", data=csv_bytes, file_name=f"Tracker_{prefijo}_{date_str}.csv")
        else:
            st.warning("No data found for this partner.")