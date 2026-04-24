import pandas as pd
import datetime
import io
import streamlit as st
from supabase import create_client, Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ============================================================
# SUPABASE CONFIG
# ============================================================
SUPABASE_URL = "https://ecspmmhwlcxcftkfnbbf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVjc3BtbWh3bGN4Y2Z0a2ZuYmJmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4OTA4MDgsImV4cCI6MjA5MjQ2NjgwOH0.lAVH4ljNR2TKt-vU1aVZt69mg0YelXP4GRgxXTGFdrA"

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# CONFIGURATION & MAPPINGS
# ============================================================
st.set_page_config(page_title="Sales Automation System", layout="wide")

# ---- PLANO 2 ----
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

# ---- PLANO 1 ----
TAG_MAPPING_PLANO1 = {
    'unomas-station-tracker-breakfast': 'Uno Mas Breakfast',
    'unomas-station-tracker':           'Uno Mas Lunch',
    'urbn-breakfast-station-tracker':   'Grab & Go Breakfast Sandwich',
    'g-g-station-tracker':              'Grab & Go Trading Post',
    'g-g-breakfast':                    'Grab & Go Breakfast Sandwich',
    'station-tracker-omelet':           'Main Ingredient Omelet',
    'salad-bar-station-tracker':        'Salad Bar & Main Ingredient',
    'salt-and-sesame-station-tracker':  'Salt & Sesame',
    'fiamma-entree-station-tracker':    'Fiamma Entrée',
    'fiamma-pizza-station-tracker':     'Fiamma Pizza',
    'sushi-station-tracker':            'Grab n Go Sushi',
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
    "ODA": 0.25, "HALAL": 0.20, "A2B": 0.25, "SUSHI": 0.25,
}

DAYS_NAME = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']


# ============================================================
# SUPABASE HELPERS
# ============================================================
def save_day_to_supabase(location: str, report_dt: datetime.datetime, report_day: str, daily_counts: dict):
    """Upsert daily station counts into Supabase. Returns (success, message)."""
    try:
        supabase = get_supabase()
        records = []
        for station, count in daily_counts.items():
            records.append({
                "location":    location,
                "report_date": report_dt.strftime('%Y-%m-%d'),
                "report_day":  report_day,
                "station":     station,
                "count":       int(count),
            })
        supabase.table("daily_sales").upsert(
            records,
            on_conflict="location,report_date,station"
        ).execute()
        return True, f"✅ {report_day} {report_dt.strftime('%m-%d-%Y')} saved to database."
    except Exception as e:
        return False, f"❌ Error saving to database: {e}"


def load_week_from_supabase(location: str, start_w: datetime.datetime, end_w: datetime.datetime):
    """Load all days in the week range for this location from Supabase."""
    try:
        supabase = get_supabase()
        resp = supabase.table("daily_sales") \
            .select("*") \
            .eq("location", location) \
            .gte("report_date", start_w.strftime('%Y-%m-%d')) \
            .lte("report_date", end_w.strftime('%Y-%m-%d')) \
            .execute()
        return resp.data or []
    except Exception as e:
        st.warning(f"Could not load data from database: {e}")
        return []


def load_all_from_supabase(location: str):
    """Load all records for a location from Supabase (for admin view)."""
    try:
        supabase = get_supabase()
        resp = supabase.table("daily_sales") \
            .select("*") \
            .eq("location", location) \
            .order("report_date", desc=True) \
            .execute()
        return resp.data or []
    except Exception as e:
        st.warning(f"Could not load records: {e}")
        return []


def delete_day_from_supabase(location: str, date_str: str):
    """Delete all records for a specific day and location."""
    try:
        supabase = get_supabase()
        supabase.table("daily_sales") \
            .delete() \
            .eq("location", location) \
            .eq("report_date", date_str) \
            .execute()
        return True, f"✅ All records for {location} on {date_str} have been deleted."
    except Exception as e:
        return False, f"❌ Error deleting records: {e}"


def delete_week_from_supabase(location: str, start_w: datetime.datetime, end_w: datetime.datetime):
    """Delete all records for a full week and location."""
    try:
        supabase = get_supabase()
        supabase.table("daily_sales") \
            .delete() \
            .eq("location", location) \
            .gte("report_date", start_w.strftime('%Y-%m-%d')) \
            .lte("report_date", end_w.strftime('%Y-%m-%d')) \
            .execute()
        return True, f"✅ All records for {location} from {start_w.strftime('%m-%d-%Y')} to {end_w.strftime('%m-%d-%Y')} have been deleted."
    except Exception as e:
        return False, f"❌ Error deleting week: {e}"


def build_weekly_tracker_from_db(db_rows: list, stations: list) -> pd.DataFrame:
    """Build the weekly tracker DataFrame from Supabase rows."""
    data = {stn: {d: 0 for d in DAYS_NAME} for stn in stations}
    for row in db_rows:
        stn = row['station']
        day = row['report_day']
        cnt = row['count']
        if stn in data and day in DAYS_NAME:
            data[stn][day] += cnt
    rows = []
    for stn in stations:
        r = {'Station': stn}
        total = 0
        for d in DAYS_NAME:
            r[d] = data[stn][d]
            total += data[stn][d]
        r['Weekly Total'] = total
        rows.append(r)
    return pd.DataFrame(rows)


def get_saved_dates_for_week(db_rows: list) -> list:
    dates = set()
    for row in db_rows:
        dates.add(row['report_date'])
    return sorted(list(dates))


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
    """
    Detect location from first line of CSV.
    - 'Plano 2' or 'Plano2'           → plano2
    - 'Plano 1', 'Plano1', or 'Plano' → plano1
      (bare 'Plano' with no number defaults to Plano 1)
    """
    uploaded_file.seek(0)
    first_line = uploaded_file.getvalue().decode('utf-8').splitlines()[0].lower()

    # Check Plano 2 first (more specific)
    if 'plano 2' in first_line or 'plano2' in first_line:
        return 'plano2'
    # Any remaining 'plano' reference → Plano 1
    if 'plano' in first_line:
        return 'plano1'
    return 'unknown'


def get_week_range(report_dt):
    offset = (report_dt.weekday() - 3) % 7
    start_week = report_dt - datetime.timedelta(days=offset)
    end_week = start_week + datetime.timedelta(days=6)
    return start_week, end_week


def load_sales_df(uploaded_file):
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, skiprows=6).fillna('')

    def clean_numeric(val):
        if isinstance(val, str):
            val = val.replace(',', '').strip()
            return int(val) if val.isdigit() else 0
        return int(val) if str(val).strip().isdigit() else 0

    df['Count'] = df['Count'].apply(clean_numeric)
    return df


# ============================================================
# EXPORT GENERATORS
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
def compute_daily_counts(df_sales, tag_mapping, stations):
    daily_counts = {stn: 0 for stn in stations}
    for _, row in df_sales.iterrows():
        tags = [t.strip() for t in str(row['Tags']).split(',')]
        for tag in tags:
            if tag in tag_mapping:
                name = tag_mapping[tag]
                if name in daily_counts:
                    daily_counts[name] += row['Count']
                break
    return daily_counts


def build_single_day_tracker(daily_counts, stations, report_day):
    rows = []
    for stn in stations:
        r = {'Station': stn}
        for d in DAYS_NAME:
            r[d] = 0
        if report_day in DAYS_NAME:
            r[report_day] = daily_counts.get(stn, 0)
        r['Weekly Total'] = daily_counts.get(stn, 0)
        rows.append(r)
    return pd.DataFrame(rows)


# ============================================================
# PARTNER EXTRACT
# ============================================================
def render_partner_extract(df_sales, report_dt, start_w, end_w, commission_rates, location_label):
    st.write("---")
    st.header(f"2. Partner Extract — {location_label}")

    default_partner = "dock-local" if "Plano 2" in location_label else "oda"
    partner_query = st.text_input(
        "Search Partner or Tag",
        value=default_partner,
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
    prefijo = partner_query.replace('-', ' ').split()[0].upper()
    fecha_invoice_str = end_w.strftime('%d%m%y')
    invoice_num = f"{prefijo}{fecha_invoice_str}"

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
            rows_combined.append({
                'Date': '', 'Day': '', 'Main St': '', 'Total Net Sales': '',
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

    aramark_rate  = commission_rates.get(prefijo, 0.20)
    partner_rate  = 1.0 - aramark_rate
    tax_val       = partner_sales * 0.0825
    partner_com   = partner_sales * partner_rate
    aramark_com   = partner_sales * aramark_rate
    total_pay_val = tax_val + partner_com
    pay_label     = f"{prefijo.capitalize()} Pay"

    st.subheader("Totals and Commissions")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net Sales",                          f"${partner_sales:,.2f}")
    m2.metric("Tax (8.25%)",                        f"${tax_val:,.2f}")
    m3.metric(f"Partner ({partner_rate*100:.0f}%)", f"${partner_com:,.2f}")
    m4.metric(f"Aramark ({aramark_rate*100:.0f}%)", f"${aramark_com:,.2f}")

    st.markdown("---")
    st.metric(label=f"💰 {pay_label}", value=f"${total_pay_val:,.2f}")

    metrics_dict = {
        "Total Net Sales":                           f"${partner_sales:,.2f}",
        "Tax (8.25%)":                               f"${tax_val:,.2f}",
        f"Partner Share ({partner_rate*100:.0f}%)":  f"${partner_com:,.2f}",
        f"Aramark Share ({aramark_rate*100:.0f}%)":  f"${aramark_com:,.2f}",
        pay_label:                                   f"${total_pay_val:,.2f}"
    }

    st.write("### Report Actions")
    c1, c2 = st.columns(2)
    with c1:
        pdf_bytes = export_partner_pdf(
            df_combined, h_info, metrics_dict,
            f"{partner_query.upper()} Partner Report — {location_label}"
        )
        st.download_button(
            "🖨️ Print PDF Report", data=pdf_bytes,
            file_name=f"Report_{partner_query}_{date_str}.pdf",
            key=f"pdf_{location_label}_{partner_query}"
        )
    with c2:
        csv_bytes = export_partner_csv(df_combined, h_info, metrics_dict)
        st.download_button(
            "📥 Download CSV Tracker", data=csv_bytes,
            file_name=f"Tracker_{partner_query}_{date_str}.csv",
            key=f"csv_{location_label}_{partner_query}"
        )


# ============================================================
# WEEKLY VIEW
# ============================================================
def render_weekly_view(location: str, location_label: str, stations: list, start_w, end_w):
    st.write("---")
    st.header(f"3. 📅 Weekly Accumulated Tracker — {location_label}")
    st.caption(f"Week: {start_w.strftime('%m-%d-%Y')} → {end_w.strftime('%m-%d-%Y')}")

    db_rows = load_week_from_supabase(location, start_w, end_w)

    if not db_rows:
        st.info("No data saved for this week yet. Upload each day's CSV and press 'Save this day'.")
        return

    saved_dates = get_saved_dates_for_week(db_rows)
    saved_days_str = ", ".join([
        datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%A %m/%d')
        for d in saved_dates
    ])
    st.success(f"📥 Days saved this week: **{saved_days_str}**")

    df_weekly = build_weekly_tracker_from_db(db_rows, stations)
    st.dataframe(df_weekly, use_container_width=True)

    h_info = {
        'invoice': 'WEEKLY',
        'start': start_w.strftime('%m-%d-%Y'),
        'end': end_w.strftime('%m-%d-%Y')
    }
    c1, c2 = st.columns(2)
    with c1:
        pdf_weekly = export_partner_pdf(
            df_weekly, h_info, {},
            f"Weekly Station Tracker — {location_label}"
        )
        st.download_button(
            "🖨️ Export Weekly Tracker (PDF)", data=pdf_weekly,
            file_name=f"WeeklyTracker_{location_label.replace(' ','_')}_{start_w.strftime('%Y-%m-%d')}.pdf",
            key=f"weekly_pdf_{location_label}"
        )
    with c2:
        csv_out = io.StringIO()
        csv_out.write(f"Weekly Tracker — {location_label}\n")
        csv_out.write(f"Week: {start_w.strftime('%m-%d-%Y')} to {end_w.strftime('%m-%d-%Y')}\n\n")
        df_weekly.to_csv(csv_out, index=False)
        st.download_button(
            "📥 Export Weekly Tracker (CSV)",
            data=csv_out.getvalue().encode('utf-8'),
            file_name=f"WeeklyTracker_{location_label.replace(' ','_')}_{start_w.strftime('%Y-%m-%d')}.csv",
            key=f"weekly_csv_{location_label}"
        )


# ============================================================
# ADMIN PANEL
# ============================================================
def render_admin_panel():
    st.write("---")
    st.header("⚙️ Administration Panel")
    st.warning("⚠️ Actions in this section permanently delete data from the database. Use with caution.")

    tab1, tab2, tab3 = st.tabs(["🗑️ Delete a Day", "🗑️ Delete a Full Week", "📋 View All Saved Records"])

    # --- Tab 1: Delete a specific day ---
    with tab1:
        st.subheader("Delete a Specific Day")
        col_a, col_b = st.columns(2)
        with col_a:
            del_location = st.selectbox("Location", ["Plano 1", "Plano 2"], key="del_day_location")
        with col_b:
            del_date = st.date_input("Date to delete", key="del_day_date")

        if st.button("🗑️ Delete this day", type="primary", key="btn_del_day"):
            ok, msg = delete_day_from_supabase(del_location, del_date.strftime('%Y-%m-%d'))
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    # --- Tab 2: Delete a full week ---
    with tab2:
        st.subheader("Delete a Full Week")
        col_c, col_d, col_e = st.columns(3)
        with col_c:
            del_week_location = st.selectbox("Location", ["Plano 1", "Plano 2"], key="del_week_location")
        with col_d:
            del_week_start = st.date_input("Week start date (Thursday)", key="del_week_start")
        with col_e:
            del_week_end = st.date_input("Week end date (Wednesday)", key="del_week_end")

        st.caption(f"This will delete ALL records for **{del_week_location}** between the selected dates.")

        # Two-step confirmation to prevent accidental deletion
        confirm = st.checkbox("I confirm I want to delete this entire week", key="confirm_week_delete")
        if confirm:
            if st.button("🗑️ Delete full week", type="primary", key="btn_del_week"):
                start_dt = datetime.datetime(del_week_start.year, del_week_start.month, del_week_start.day)
                end_dt   = datetime.datetime(del_week_end.year,   del_week_end.month,   del_week_end.day)
                ok, msg  = delete_week_from_supabase(del_week_location, start_dt, end_dt)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    # --- Tab 3: View all saved records ---
    with tab3:
        st.subheader("All Saved Records")
        view_location = st.selectbox("Filter by location", ["Plano 1", "Plano 2"], key="view_location")

        all_rows = load_all_from_supabase(view_location)
        if not all_rows:
            st.info(f"No records found for {view_location}.")
        else:
            df_all = pd.DataFrame(all_rows)[['location', 'report_date', 'report_day', 'station', 'count', 'uploaded_at']]
            df_all['report_date'] = pd.to_datetime(df_all['report_date']).dt.strftime('%m-%d-%Y')

            # Summary: which dates are saved
            unique_dates = sorted(df_all['report_date'].unique(), reverse=True)
            st.info(f"**{len(unique_dates)} day(s) saved** for {view_location}: {', '.join(unique_dates)}")

            st.dataframe(df_all, use_container_width=True)

            # Export all records as CSV
            csv_all = df_all.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download All Records (CSV)",
                data=csv_all,
                file_name=f"AllRecords_{view_location.replace(' ','_')}.csv",
                key="download_all_records"
            )


# ============================================================
# MAIN APP
# ============================================================
st.title("🚀 Sales Automation System")
st.caption("JPMC Plano — Aramark")

uploaded_file = st.file_uploader("📂 Upload 'Item Sales' CSV", type="csv")

if uploaded_file:
    # --- Parse file ---
    report_dt, report_day = get_report_info(uploaded_file)
    date_str        = report_dt.strftime('%Y-%m-%d')
    start_w, end_w  = get_week_range(report_dt)
    location        = get_location_name(uploaded_file)
    df_sales        = load_sales_df(uploaded_file)

    # --- Detect location ---
    if location == 'plano1':
        location_label   = "Plano 1"
        tag_mapping      = TAG_MAPPING_PLANO1
        stations         = STATIONS_PLANO1
        commission_rates = COMMISSION_RATES_PLANO1
    elif location == 'plano2':
        location_label   = "Plano 2"
        tag_mapping      = TAG_MAPPING_PLANO2
        stations         = STATIONS_PLANO2
        commission_rates = COMMISSION_RATES_PLANO2
    else:
        st.warning("⚠️ Location not detected automatically. Please select:")
        loc_choice = st.radio("Location", ["Plano 1", "Plano 2"], horizontal=True)
        if loc_choice == "Plano 1":
            location_label   = "Plano 1"
            tag_mapping      = TAG_MAPPING_PLANO1
            stations         = STATIONS_PLANO1
            commission_rates = COMMISSION_RATES_PLANO1
        else:
            location_label   = "Plano 2"
            tag_mapping      = TAG_MAPPING_PLANO2
            stations         = STATIONS_PLANO2
            commission_rates = COMMISSION_RATES_PLANO2

    st.success(f"📍 **{location_label}** | {report_day}, {report_dt.strftime('%B %d, %Y')} | Week: {start_w.strftime('%m/%d')} – {end_w.strftime('%m/%d/%Y')}")

    # --- Raw data ---
    with st.expander("🔍 View Raw CSV Data"):
        st.dataframe(df_sales[['Item', 'Count', 'Pre-tax Total']], use_container_width=True)

    # ---- 1. STATION TRACKER ----
    st.header(f"1. Station Tracker — {location_label} ({report_day})")

    daily_counts = compute_daily_counts(df_sales, tag_mapping, stations)
    df_tracker   = build_single_day_tracker(daily_counts, stations, report_day)
    st.dataframe(df_tracker, use_container_width=True)

    col_pdf, col_save = st.columns(2)
    with col_pdf:
        pdf_tracker = export_partner_pdf(
            df_tracker,
            {"invoice": "N/A", "start": date_str, "end": date_str},
            {},
            f"Station Tracker — {location_label} — {report_day} {date_str}"
        )
        st.download_button(
            "🖨️ Print Daily Tracker (PDF)",
            data=pdf_tracker,
            file_name=f"Tracker_{location_label.replace(' ','_')}_{date_str}.pdf"
        )
    with col_save:
        if st.button("💾 Save this day to database", type="primary"):
            ok, msg = save_day_to_supabase(location_label, report_dt, report_day, daily_counts)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    # ---- 2. PARTNER EXTRACT ----
    render_partner_extract(df_sales, report_dt, start_w, end_w, commission_rates, location_label)

    # ---- 3. WEEKLY VIEW ----
    render_weekly_view(location_label, location_label, stations, start_w, end_w)

# ---- 4. ADMIN PANEL (always visible, no file needed) ----
render_admin_panel()