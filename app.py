import pandas as pd
import datetime
import io
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ============================================================
# CONFIGURATION & MAPPINGS
# ============================================================
st.set_page_config(page_title="Sales Automation System", layout="wide")

# ---- PLANO 2 (original) ----
TAG_MAPPING_PLANO2 = {
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

STATIONS_PLANO2 = [
    'Far East Made to Order', 'Far Easet Express', 'Far East Protein Only',
    'Far East Shrimp Entrée', 'Far East Side/Extra Protein/Shrimp/Egg Rolls',
    'Elevated Table Entrée', 'Elevated Table Protein Only', 'Elevated Table Side Only',
    'Modern Greens', 'Modern Greens Soup', 'Market Bar', 'Hopes Cookies',
    'Far East Sushi', 'Dock Local Special', '3Taco/Lobster', '2Taco/Bowl',
    'Lobster Roll Combo', 'Side', 'Protein'
]

COMMISSION_RATES_PLANO2 = {
    "DOCK": 0.20, "ODA": 0.25, "HALAL": 0.20,
    "A2B": 0.25, "LUCIS": 0.20, "SUSHI": 0.25
}

# ---- PLANO 1 (new) ----
TAG_MAPPING_PLANO1 = {
    'unomas-station-tracker-breakfast': 'Uno Mas Breakfast',
    'unomas-station-tracker':           'Uno Mas Lunch',
    'urbn-breakfast-station-tracker':   'Grab & Go Breakfast Sandwich',
    'g-g-station-tracker':              'Grab & Go Trading Post',
    'station-tracker-omelet':           'Main Ingredient Omelet',
    'salad-bar-station-tracker':        'Salad Bar & Main Ingredient',
    'salt-and-sesame-station-tracker':  'Salt & Sesame',
    'fiamma-entree-station-tracker':    'Fiamma Entrée',
    'fiamma-pizza-station-tracker':     'Fiamma Pizza',
    'sushi-station-tracker':            'Grab n Go Sushi',
    'g-g-breakfast':                    'Grab & Go Breakfast Sandwich',  # fallback tag
    'soup-station-tracker':             'Soup',
    'oatmeal-station-tracker':          'Oatmeal',
    'cookie-station-tracker':           'Hopes Cookies',
    'slice-of-cake-station-tracker':    'Slice of Cake/Cheesecake',
    'lays-tracker':                     'Lays',
}

STATIONS_PLANO1 = [
    'Uno Mas Breakfast',
    'Uno Mas Lunch',
    'Grab & Go Breakfast Sandwich',
    'Grab & Go Trading Post',
    'Main Ingredient Omelet',
    'Continental (Pastry)',
    'Salad Bar & Main Ingredient',
    'Salt & Sesame',
    'Fiamma Entrée',
    'Fiamma Pizza',
    'Grab n Go Sushi',
    'Urban Burger',
    'Soup',
    'Oatmeal',
    'Hopes Cookies',
    'Slice of Cake/Cheesecake',
    'Smokehouse',
    'Lays',
]

COMMISSION_RATES_PLANO1 = {
    "ODA":   0.25,
    "HALAL": 0.20,
    "A2B":   0.25,
    "SUSHI": 0.25,
}

# ---- Shared ----
DAYS_NAME = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']


# ============================================================
# SUPPORT FUNCTIONS
# ============================================================
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


def get_location_name(uploaded_file):
    """Read first line to detect if it's Plano 1 or Plano 2."""
    uploaded_file.seek(0)
    first_line = uploaded_file.getvalue().decode('utf-8').splitlines()[0]
    first_line_lower = first_line.lower()
    if 'plano 1' in first_line_lower or 'plano1' in first_line_lower or 'main st' in first_line_lower:
        return 'plano1'
    if 'plano 2' in first_line_lower or 'plano2' in first_line_lower or 'far east' in first_line_lower:
        return 'plano2'
    return 'unknown'


def get_week_range(report_dt):
    offset = (report_dt.weekday() - 3) % 7
    start_week = report_dt - datetime.timedelta(days=offset)
    end_week = start_week + datetime.timedelta(days=6)
    return start_week, end_week


def load_sales_df(uploaded_file):
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, skiprows=6).fillna('')

    def clean_numeric_column(val):
        if isinstance(val, str):
            val = val.replace(',', '').strip()
            return int(val) if val.isdigit() else 0
        return int(val) if str(val).isdigit() else 0

    df['Count'] = df['Count'].apply(clean_numeric_column)
    return df


# ============================================================
# EXPORT GENERATORS (shared)
# ============================================================
def export_partner_pdf(df_combined, header_info, metrics, title):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"<b>Invoice Number:</b> {header_info.get('invoice', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Week Sales From:</b> {header_info.get('start', '')} <b>thru</b> {header_info.get('end', '')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(title, styles['Title']))

    dfs_to_process = df_combined if isinstance(df_combined, list) else [df_combined]

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
    output.write(f",,,Invoice Number,{header_info['invoice']}\n")
    output.write(f",Week Sales From,,{header_info['start']}\n")
    output.write(f",,thru,{header_info['end']}\n\n")
    df_combined.to_csv(output, index=False)
    output.write("\nTAXES AND COMMISSIONS\n")
    for label, val in metrics.items():
        output.write(f"{label},{val}\n")
    return output.getvalue().encode('utf-8')


# ============================================================
# STATION TRACKER BUILDER
# ============================================================
def build_station_tracker(df_sales, tag_mapping, stations, report_day):
    daily_counts = {stn: 0 for stn in stations}
    for _, row in df_sales.iterrows():
        tags = [t.strip() for t in str(row['Tags']).split(',')]
        for tag in tags:
            if tag in tag_mapping:
                name = tag_mapping[tag]
                if name in daily_counts:
                    daily_counts[name] += row['Count']
                break

    tracker_data = []
    for stn in stations:
        row_data = {'Station': stn}
        for d in DAYS_NAME:
            row_data[d] = 0
        if report_day in DAYS_NAME:
            row_data[report_day] = daily_counts[stn]
        row_data['Weekly Total'] = daily_counts[stn]
        tracker_data.append(row_data)

    return pd.DataFrame(tracker_data)


# ============================================================
# PARTNER EXTRACT (shared logic)
# ============================================================
def render_partner_extract(df_sales, report_dt, start_w, end_w, commission_rates, location_label):
    st.write("---")
    st.header(f"2. Partner Extract — {location_label}")

    partner_query = st.text_input(
        "Search Partner or Tag",
        value="dock-local" if location_label == "Plano 2" else "oda",
        key=f"partner_query_{location_label}"
    ).lower()

    if not partner_query:
        return

    date_str = report_dt.strftime('%Y-%m-%d')
    partner_sales = 0.0
    item_details = []

    for _, row in df_sales.iterrows():
        tags = [t.strip().lower() for t in str(row['Tags']).split(',')]
        if any(partner_query in t for t in tags):
            val = clean_money(row['Pre-tax Total'])
            partner_sales += val
            item_details.append({'Item': row['Item'], 'Count': row['Count']})

    if not item_details:
        st.warning("No data found for this partner.")
        return

    df_items = pd.DataFrame(item_details).groupby('Item')['Count'].sum().reset_index()
    rows_combined = []

    prefijo = partner_query.replace('-', ' ').split()[0].upper()
    fecha_invoice_str = end_w.strftime('%d%m%y')
    invoice_num = f"{prefijo}{fecha_invoice_str}"

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
            rows_combined.append({
                'Date': '', 'Day': '', 'Main St': '',
                'Total Net Sales': '',
                'Item Detail': df_items.iloc[i]['Item'],
                'Total Count': df_items.iloc[i]['Count']
            })

    df_combined = pd.DataFrame(rows_combined)
    h_info = {
        'invoice': invoice_num,
        'start': start_w.strftime('%m-%d-%Y'),
        'end': end_w.strftime('%m-%d-%Y')
    }

    st.info(f"**Invoice:** {h_info['invoice']} | **Period:** {h_info['start']} to {h_info['end']}")
    st.table(df_combined)

    aramark_rate = commission_rates.get(prefijo, 0.20)
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

    if prefijo in ["SUSHI", "A2B"]:
        st.markdown("---")
        st.subheader(f"📅 {prefijo} Weekly Management")
        col_acc1, col_acc2 = st.columns(2)

        week_key = f'weekly_accumulator_{location_label}_{prefijo}'
        if week_key not in st.session_state:
            st.session_state[week_key] = []

        with col_acc1:
            if st.button(f"➕ Add {report_dt.strftime('%A')} to Weekly", key=f"add_{location_label}_{prefijo}"):
                st.session_state[week_key].append({
                    'date': report_dt,
                    'sales': partner_sales,
                    'items': item_details
                })
                st.success(f"Added! Days stored: {len(st.session_state[week_key])}")

        with col_acc2:
            if st.button("🗑️ Reset Weekly Memory", key=f"reset_{location_label}_{prefijo}"):
                st.session_state[week_key] = []
                st.rerun()

        if st.session_state[week_key]:
            st.write("**Days in memory:**")
            for entry in st.session_state[week_key]:
                st.write(f"- {entry['date'].strftime('%m-%d-%Y')}: ${entry['sales']:,.2f}")

    st.write("### Single Day Actions")
    st.markdown("---")
    st.metric(label=f"💰 {pay_label}", value=f"${total_pay_val:,.2f}")

    metrics_dict = {
        "Total Net Sales": f"${partner_sales:,.2f}",
        "Tax (8.25%)": f"${tax_val:,.2f}",
        f"Partner Share ({partner_rate*100:.0f}%)": f"${partner_com:,.2f}",
        f"Aramark Share ({aramark_rate*100:.0f}%)": f"${aramark_com:,.2f}",
        pay_label: f"${total_pay_val:,.2f}"
    }

    st.write("### Report Actions")
    c1, c2 = st.columns(2)
    with c1:
        pdf_bytes = export_partner_pdf(df_combined, h_info, metrics_dict, f"{partner_query.upper()} Partner Report — {location_label}")
        st.download_button("🖨️ Print PDF Report", data=pdf_bytes, file_name=f"Report_{partner_query}_{date_str}.pdf", key=f"pdf_{location_label}_{partner_query}")
    with c2:
        csv_bytes = export_partner_csv(df_combined, h_info, metrics_dict)
        st.download_button("📥 Download CSV Tracker", data=csv_bytes, file_name=f"Tracker_{partner_query}_{date_str}.csv", key=f"csv_{location_label}_{partner_query}")


# ============================================================
# STREAMLIT INTERFACE
# ============================================================
st.title("🚀 Sales Automation System")

# Initialize session states
if 'weekly_accumulator' not in st.session_state:
    st.session_state.weekly_accumulator = []

# ---- File upload ----
uploaded_file = st.file_uploader("Upload 'Item Sales' file (CSV)", type="csv")

if uploaded_file:
    report_dt, report_day = get_report_info(uploaded_file)
    date_str = report_dt.strftime('%Y-%m-%d')
    start_w, end_w = get_week_range(report_dt)
    location = get_location_name(uploaded_file)
    df_sales = load_sales_df(uploaded_file)

    # Detect location and show label
    if location == 'plano1':
        location_label = "Plano 1 — Main St"
        tag_mapping = TAG_MAPPING_PLANO1
        stations = STATIONS_PLANO1
        commission_rates = COMMISSION_RATES_PLANO1
        st.success(f"📍 **Location detected: {location_label}**  |  Date: {report_dt.strftime('%A, %B %d %Y')}")
    elif location == 'plano2':
        location_label = "Plano 2"
        tag_mapping = TAG_MAPPING_PLANO2
        stations = STATIONS_PLANO2
        commission_rates = COMMISSION_RATES_PLANO2
        st.success(f"📍 **Location detected: {location_label}**  |  Date: {report_dt.strftime('%A, %B %d %Y')}")
    else:
        # Ask user to select manually
        st.warning("⚠️ Could not auto-detect location. Please select manually:")
        loc_choice = st.radio("Select Location", ["Plano 1 — Main St", "Plano 2"], horizontal=True)
        if loc_choice == "Plano 1 — Main St":
            location_label = "Plano 1 — Main St"
            tag_mapping = TAG_MAPPING_PLANO1
            stations = STATIONS_PLANO1
            commission_rates = COMMISSION_RATES_PLANO1
        else:
            location_label = "Plano 2"
            tag_mapping = TAG_MAPPING_PLANO2
            stations = STATIONS_PLANO2
            commission_rates = COMMISSION_RATES_PLANO2

    # ---- Raw Data ----
    with st.expander("View Filtered Raw Data"):
        st.dataframe(df_sales[['Item', 'Count', 'Pre-tax Total']], use_container_width=True)

    # ---- 1. STATION TRACKER ----
    st.header(f"1. Station Tracker — {location_label}")
    df_tracker = build_station_tracker(df_sales, tag_mapping, stations, report_day)
    st.dataframe(df_tracker, use_container_width=True)

    pdf_tracker = export_partner_pdf(
        df_tracker,
        {"invoice": "N/A", "start": date_str, "end": date_str},
        {},
        f"Station Tracker — {location_label}"
    )
    st.download_button(
        "🖨️ Print Station Tracker (PDF)",
        data=pdf_tracker,
        file_name=f"Tracker_{location_label.replace(' ', '_')}_{date_str}.pdf"
    )

    # ---- 2. PARTNER EXTRACT ----
    render_partner_extract(df_sales, report_dt, start_w, end_w, commission_rates, location_label)