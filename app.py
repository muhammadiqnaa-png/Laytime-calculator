import streamlit as st
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd

st.set_page_config(page_title="⚓ Voyage Report", layout="wide")
st.title("⚓ Voyage Report – Detention Calculation")

# ---------------- Helpers ----------------
def default_time():
    return time(8, 0)

def safe_datetime(d: date, t: time):
    return datetime.combine(d, t)

def duration_hours_between(first_dt: datetime, last_dt: datetime):
    return max(0.0, (last_dt - first_dt).total_seconds() / 3600.0)

def format_rp(x):
    try:
        return "Rp {:,}".format(int(round(x))).replace(",", ".")
    except:
        return f"Rp {x}"

def format_cargo_indonesia(x, decimals=3):
    """
    Format number ke style Indonesia:
    - thousands separator = '.'
    - decimal separator = ','
    Example: 7500.335 -> '7.500,335'
    """
    try:
        # ensure float
        xf = float(x)
    except:
        return ""
    # format with python default (',' thousands and '.' decimal)
    fmt = f"{{:,.{decimals}f}}".format(xf)  # e.g. '7,500.335'
    # swap to desired (','->temp, '.'->',', temp->'.')
    s = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

# ---------------- PDF builder (no QR) ----------------
def build_pdf(ctx):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=6, spaceAfter=6, textColor=colors.darkblue))
    elems = []

    elems.append(Paragraph("⚓ VOYAGE REPORT – LAYTIME CALCULATION", styles["CenterTitle"]))

    # Info order per request:
    # 1. Tug Boat, 2. Barge, 3. Shipper, 4. Laycan, 5. POL, 6. POD, 7. Total Cargo, 8. Free Time, 9. Rate Demurrage
    total_cargo_disp = ""
    if ctx.get("total_cargo") is not None:
        total_cargo_disp = f"{format_cargo_indonesia(ctx['total_cargo'])} MT"
    info = [
        ["Tug Boat", ctx.get("tugboat","")],
        ["Barge", ctx.get("barge","")],
        ["Shipper", ctx.get("shipper","")],
        ["Laycan", ctx.get("laycan","")],
        ["POL", ctx.get("pol","")],
        ["POD", ctx.get("pod","")],
        ["Total Cargo", total_cargo_disp],
        ["Prorata", f"{ctx['prorata']:.2f} Hari"],
        ["Rate Demurrage", f"{format_rp(ctx['rate_per_day'])}/Hari"],
    ]
    t_info = Table(info, colWidths=[130, 410])
    t_info.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                                ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
                                ("FONTSIZE", (0,0), (-1,-1), 9)]))
    elems += [Spacer(1,6), Paragraph("<b>Information</b>", styles["SubHeader"]), t_info, Spacer(1,8)]

    def section(title, rows):
        data = [["No", "Date", "Time", "Status", "Duration (Hours)"]]
        for i, r in enumerate(rows, start=1):
            dur = r.get("Duration")
            # show '-' when None or NaN or zero-empty
            dur_display = "-" if (dur is None or (isinstance(dur, float) and (pd.isna(dur) or dur==0.0))) else f"{dur:.2f}"
            data.append([str(i),
                         r["Date"].strftime("%d %b %Y"),
                         r["Time"].strftime("%H:%M"),
                         r["Status"],
                         dur_display
                        ])
        colw = [30, 90, 60, 270, 90]
        t = Table(data, colWidths=colw, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                               ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                               ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                               ("FONTSIZE", (0,0), (-1,-1), 9)]))
        elems.append(Paragraph(f"<b>{title}</b>", styles["SubHeader"]))
        elems.append(t)
        elems.append(Spacer(1,8))

    section("Voyage POL", ctx["pol_rows"])
    section("Voyage POD", ctx["pod_rows"])

    summary = [
        ["Duration POL", f"{ctx['pol_hours']:.2f} hours ({ctx['pol_hours']/24:.2f} day)"],
        ["Duration POD", f"{ctx['pod_hours']:.2f} hours ({ctx['pod_hours']/24:.2f} day)"],
        ["Total (POL+POD)", f"{ctx['total_hours']:.2f} Hours ({ctx['total_days']:.2f} day)"],
        ["Free Time", f"{ctx['prorata']:.2f} day"],
        ["Demurrage Days", f"{ctx['detention_days']:.2f} day"],
        ["Total Detention", format_rp(ctx['total_cost'])]
    ]
    t_sum = Table(summary, colWidths=[130, 410])
    t_sum.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                               ("BACKGROUND", (0,5), (-1,5), colors.whitesmoke),
                               ("TEXTCOLOR", (0,5), (-1,5), colors.red),
                               ("FONTNAME", (0,0), (-1,-1), "Helvetica")]))
    elems += [Paragraph("<b>Summary</b>", styles["SubHeader"]), t_sum, Spacer(1,8)]

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# ---------------- Session state defaults ----------------
if "pol_rows" not in st.session_state:
    st.session_state.pol_rows = []
if "pod_rows" not in st.session_state:
    st.session_state.pod_rows = []
if "calc_done" not in st.session_state:
    st.session_state.calc_done = False
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None
if "excel_data" not in st.session_state:
    st.session_state.excel_data = None
if "excel_filename" not in st.session_state:
    st.session_state.excel_filename = None

# ---------------- Input header ----------------
st.header("📥 Data Utama")
col1, col2 = st.columns(2)
with col1:
    tugboat = st.text_input("Tug Boat")
    pol = st.text_input("Port of Loading (POL)")
    shipper = st.text_input("Shipper")
    laycan = st.text_input("Laycan")
    total_cargo = st.number_input("Total Cargo (MT)", min_value=0.0, value=0.0, step=0.001, format="%.3f")
with col2:
    barge = st.text_input("Barge")
    pod = st.text_input("Port of Discharge (POD)")
    

col3, col4 = st.columns(2)
with col3:
    prorata = st.number_input("Prorata (Day)", 0.0, step=0.5, value=0.0)
with col4:
    rate_per_day = st.number_input("Rate Detention (Rp/Day)", 0.0, step=100000.0, value=0.0)

st.markdown("**Catatan:** Isi `Status` bebas ketik. Tandai **Start** dan **Stop** dengan checkbox pada tiap baris (kanan). Sistem akan pasangan Start→Stop berurutan untuk menghitung durasi (jam).")
st.markdown("---")

# ---------------- POL input (manual rows with Start/Stop) ----------------
st.subheader("1️⃣ Voyage Events – POL")
if st.button("➕ Tambah Event POL"):
    st.session_state.pol_rows.append({
        "Date": date.today(), "Time": default_time(), "Status": "", "Start": False, "Stop": False, "Duration": None
    })

new_pol = []
for i, row in enumerate(st.session_state.pol_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    row.setdefault("Start", False)
    row.setdefault("Stop", False)
    row.setdefault("Duration", None)

    cols = st.columns([0.3, 2, 1, 2, 0.7, 0.6])
    cols[0].markdown(f"**{i+1}**")
    d = cols[1].date_input("", row["Date"], key=f"pol_date_{i}")
    t = cols[2].time_input("", row["Time"], key=f"pol_time_{i}")
    s = cols[3].text_input("", row["Status"], key=f"pol_status_{i}")
    start_cb = cols[4].checkbox("Start", value=row["Start"], key=f"pol_start_{i}")
    stop_cb = cols[5].checkbox("Stop", value=row["Stop"], key=f"pol_stop_{i}")
    rem = st.button("❌", key=f"pol_del_{i}_btn")
    # if remove pressed, skip adding this row to new_pol
    if not rem:
        new_pol.append({"Date": d, "Time": t, "Status": s, "Start": start_cb, "Stop": stop_cb, "Duration": None})
st.session_state.pol_rows = new_pol

st.markdown("---")

# ---------------- POD input ----------------
st.subheader("2️⃣ Voyage Events – POD")
if st.button("➕ Tambah Event POD"):
    st.session_state.pod_rows.append({
        "Date": date.today(), "Time": default_time(), "Status": "", "Start": False, "Stop": False, "Duration": None
    })

new_pod = []
for i, row in enumerate(st.session_state.pod_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    row.setdefault("Start", False)
    row.setdefault("Stop", False)
    row.setdefault("Duration", None)

    cols = st.columns([0.3, 2, 1, 2, 0.7, 0.6])
    cols[0].markdown(f"**{i+1}**")
    d = cols[1].date_input("", row["Date"], key=f"pod_date_{i}")
    t = cols[2].time_input("", row["Time"], key=f"pod_time_{i}")
    s = cols[3].text_input("", row["Status"], key=f"pod_status_{i}")
    start_cb = cols[4].checkbox("Start", value=row["Start"], key=f"pod_start_{i}")
    stop_cb = cols[5].checkbox("Stop", value=row["Stop"], key=f"pod_stop_{i}")
    rem = st.button("❌", key=f"pod_del_{i}_btn")
    if not rem:
        new_pod.append({"Date": d, "Time": t, "Status": s, "Start": start_cb, "Stop": stop_cb, "Duration": None})
st.session_state.pod_rows = new_pod

st.markdown("---")

# ---------------- Core pairing calc: Start -> Stop ----------------
def calc_by_checkboxes(rows):
    """
    rows: list of dict with keys Date, Time, Status, Start (bool), Stop (bool)
    returns: enriched_rows (list with Duration populated on Stop rows), total_hours
    - pairs each Start with the next Stop (chronologically)
    - supports multiple blocks
    - if Start exists without Stop, auto-close to now and append synthetic row
    """
    if not rows:
        return [], 0.0

    # sort rows by datetime
    sorted_rows = sorted(rows, key=lambda r: safe_datetime(r["Date"], r["Time"]))
    enriched = []
    total_hours = 0.0
    start_time = None

    for r in sorted_rows:
        row_copy = r.copy()
        row_copy["Duration"] = None  # default empty
        dt = safe_datetime(r["Date"], r["Time"])
        # if this row is checked as Start -> open block
        if r.get("Start"):
            start_time = dt
        # if this row is checked as Stop and there is an open start -> close and compute
        if r.get("Stop") and start_time:
            dur = duration_hours_between(start_time, dt)
            row_copy["Duration"] = dur
            total_hours += dur
            start_time = None  # close block
        enriched.append(row_copy)

    # if block still open at end -> auto-close to now, append synthetic row
    if start_time:
        now = datetime.now()
        dur = duration_hours_between(start_time, now)
        total_hours += dur
        enriched.append({
            "Date": now.date(),
            "Time": now.time().replace(microsecond=0),
            "Status": "OPEN BLOCK (auto-close to now)",
            "Start": False,
            "Stop": False,
            "Duration": dur
        })

    return enriched, total_hours

# ---------------- Calculate button ----------------
if st.button("⚙️ Calculate Laytime"):
    pol_enriched, pol_hours = calc_by_checkboxes(st.session_state.pol_rows)
    pod_enriched, pod_hours = calc_by_checkboxes(st.session_state.pod_rows)

    total_hours = pol_hours + pod_hours
    total_days = total_hours / 24.0
    detention_days = max(0.0, total_days - prorata)
    total_cost = detention_days * rate_per_day

    ctx = {
        "tugboat": tugboat, "barge": barge, "pol": pol, "pod": pod,
        "shipper": shipper, "laycan": laycan,
        "prorata": prorata, "rate_per_day": rate_per_day,
        "pol_rows": pol_enriched, "pod_rows": pod_enriched,
        "pol_hours": pol_hours, "pod_hours": pod_hours,
        "total_hours": total_hours, "total_days": total_days,
        "detention_days": detention_days, "total_cost": total_cost,
        "total_cargo": total_cargo
    }

    # ---------------- Prepare Excel (single sheet) ----------------
    def df_from_enriched(enriched, section_name):
        if not enriched:
            return pd.DataFrame(columns=["Section", "Date", "Time", "Status", "Start", "Stop", "Duration (hrs)"])
        df = pd.DataFrame(enriched).copy()
        # ensure columns present
        for c in ["Start", "Stop", "Duration"]:
            if c not in df.columns:
                df[c] = pd.NA
        df["Date"] = df["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df["Time"] = df["Time"].apply(lambda t: t.strftime("%H:%M"))
        df = df.rename(columns={"Duration": "Duration (hrs)"})
        df.insert(0, "Section", section_name)
        # keep desired order
        cols = ["Section", "Date", "Time", "Status", "Start", "Stop", "Duration (hrs)"]
        return df[cols]

    df_pol = df_from_enriched(pol_enriched, "POL")
    df_pod = df_from_enriched(pod_enriched, "POD")
    combined = pd.concat([df_pol, df_pod], ignore_index=True, sort=False)

    # summary rows (as separate small DF we will write below combined)
    summary_rows = [
        ["SUMMARY", "", "", "Total Cargo", f"{format_cargo_indonesia(total_cargo)} MT"],
        ["SUMMARY", "", "", "Durasi POL (Hour)", f"{pol_hours:.2f}"],
        ["SUMMARY", "", "", "Durasi POD (Hour)", f"{pod_hours:.2f}"],
        ["SUMMARY", "", "", "Total Hour", f"{total_hours:.2f}"],
        ["SUMMARY", "", "", "Total Day", f"{total_days:.2f}"],
        ["SUMMARY", "", "", "Prorata (Day)", f"{prorata:.2f}"],
        ["SUMMARY", "", "", "Demurrage Days", f"{detention_days:.2f}"],
        ["SUMMARY", "", "", "Total Detention (Rp)", format_rp(total_cost)],
    ]
    df_summary = pd.DataFrame(summary_rows, columns=["Section", "Date", "Time", "Parameter", "Value"])

    # write excel buffer
    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        combined.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=0)
        start_summary_row = len(combined) + 3
        df_summary.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=start_summary_row)
        # basic formatting
        workbook = writer.book
        worksheet = writer.sheets["LAYTIME_REPORT"]
        header_fmt = workbook.add_format({"bold": True, "align": "center", "bg_color": "#DCE6F1", "border": 1})
        for col_num, value in enumerate(combined.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 18)
        # bold SUMMARY label
        bold = workbook.add_format({"bold": True})
        worksheet.write(start_summary_row, 0, "SUMMARY", bold)

    excel_buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Laytime_Report_{timestamp}.xlsx"

    # ---------------- Build PDF (no QR) ----------------
    pdf_data = build_pdf(ctx)

    # store in session for download & preview
    st.session_state.excel_data = excel_buf.getvalue()
    st.session_state.excel_filename = excel_filename
    st.session_state.pdf_data = pdf_data
    st.session_state.calc_done = True
    st.session_state.ctx = ctx

# ---------------- Output area ----------------
if st.session_state.get("calc_done"):
    ctx = st.session_state.ctx
    st.subheader("📊 Summary")
    st.write(f"POL Duration: **{ctx['pol_hours']:.2f} hour** ({ctx['pol_hours']/24:.2f} day)")
    st.write(f"POD Duration: **{ctx['pod_hours']:.2f} hour** ({ctx['pod_hours']/24:.2f} day)")
    st.write(f"Total Duration: **{ctx['total_hours']:.2f} hour** ({ctx['total_days']:.2f} day)")
    st.write(f"Prorata: {ctx['prorata']:.2f} day")
    st.write(f"Detention Days: **{ctx['detention_days']:.2f} day**")
    st.write(f"Total Demurrage: **{format_rp(ctx['total_cost'])}**")

    st.markdown("### Preview POL + POD (lihat Excel untuk kolom Start/Stop detail)")
    # show preview: combine but only show columns Date/Time/Status/Duration for compact view
    preview_pol = pd.DataFrame(ctx["pol_rows"]).copy()
    preview_pod = pd.DataFrame(ctx["pod_rows"]).copy()
    def preview_df(df):
        if df.empty:
            return pd.DataFrame(columns=["Date","Time","Status","Duration"])
        df2 = df.rename(columns={"Duration":"Duration (hrs)"})
        df2["Date"] = df2["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df2["Time"] = df2["Time"].apply(lambda t: t.strftime("%H:%M"))
        df2["Duration (hrs)"] = df2["Duration (hrs)"].apply(lambda v: "" if (v is None or (isinstance(v,float) and pd.isna(v))) else f"{v:.2f}")
        return df2[["Date","Time","Status","Duration (hrs)"]]

    st.markdown("**POL**")
    st.dataframe(preview_df(preview_pol), use_container_width=True)
    st.markdown("**POD**")
    st.dataframe(preview_df(preview_pod), use_container_width=True)

    st.download_button("📄 Download PDF", st.session_state.pdf_data, "Laytime_Report.pdf", "application/pdf")
    st.download_button("📊 Download Excel (1 sheet)", st.session_state.excel_data, st.session_state.excel_filename,
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
