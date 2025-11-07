import streamlit as st
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
import pandas as pd

st.set_page_config(page_title="⚓ Voyage Report", layout="wide")
st.title("⚓ Voyage Report – Detention / Demurrage Calculator (Flexible Start/Stop)")

# ===== Helper =====
def default_time():
    return time(8, 0)

def safe_datetime(d: date, t: time):
    return datetime.combine(d, t)

def duration_hours_between(first_dt: datetime, last_dt: datetime):
    diff = (last_dt - first_dt).total_seconds() / 3600.0
    return max(0.0, diff)

def format_rp(x):
    try:
        return "Rp {:,}".format(int(round(x))).replace(",", ".")
    except:
        return f"Rp {x}"

# ===== PDF Builder (sama seperti sebelumnya) =====
def build_pdf(ctx, excel_link=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=8, spaceAfter=6, textColor=colors.darkblue))
    elems = []

    elems.append(Paragraph("⚓ VOYAGE REPORT – DETENTION / DEMURRAGE", styles["CenterTitle"]))

    # Info
    info = [
        ["Tug Boat", ctx.get("tugboat","")],
        ["Barge", ctx.get("barge","")],
        ["POL", ctx.get("pol","")],
        ["POD", ctx.get("pod","")],
        ["Shipper", ctx.get("shipper","")],
        ["Laycan", ctx.get("laycan","")],
        ["Prorata (Free Time)", f"{ctx['prorata']:.2f} Hari"],
        ["Rate Demurrage", f"{format_rp(ctx['rate_per_day'])}/Hari"],
    ]
    t_info = Table(info, colWidths=[150, 350])
    t_info.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10)
    ]))
    elems += [Spacer(1,6), Paragraph("<b>Informasi Umum</b>", styles["SubHeader"]), t_info, Spacer(1,10)]

    def section(title, rows):
        data = [["No", "Date", "Time", "Status", "Block ID", "Duration (hrs)"]]
        for i, r in enumerate(rows, start=1):
            dur_display = "" if pd.isna(r.get("Duration (hrs)")) else f"{r.get('Duration (hrs)'):.2f}"
            data.append([
                str(i),
                r["Date"].strftime("%d %b %Y"),
                r["Time"].strftime("%H:%M"),
                r["Status"],
                r.get("Block ID", ""),
                dur_display
            ])
        t = Table(data, colWidths=[30, 100, 60, 220, 60, 60])
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9)
        ]))
        elems.append(Paragraph(f"<b>{title}</b>", styles["SubHeader"]))
        elems.append(t)
        elems.append(Spacer(1,8))

    section("Voyage POL", ctx["pol_rows"])
    section("Voyage POD", ctx["pod_rows"])

    summary = [
        ["Durasi POL", f"{ctx['pol_hours']:.2f} jam ({ctx['pol_hours']/24:.2f} hari)"],
        ["Durasi POD", f"{ctx['pod_hours']:.2f} jam ({ctx['pod_hours']/24:.2f} hari)"],
        ["Total (POL+POD)", f"{ctx['total_hours']:.2f} jam ({ctx['total_days']:.2f} hari)"],
        ["Prorata (Free Time)", f"{ctx['prorata']:.2f} hari"],
        ["Demurrage Days", f"{ctx['detention_days']:.2f} hari"],
        ["Total Biaya", format_rp(ctx['total_cost'])]
    ]
    t_sum = Table(summary, colWidths=[200, 300])
    t_sum.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,5), (-1,5), colors.whitesmoke),
        ("TEXTCOLOR", (0,5), (-1,5), colors.red)
    ]))
    elems += [Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]), t_sum, Spacer(1,12)]

    if excel_link:
        elems.append(Paragraph("<b>Scan QR untuk versi Excel yang dapat diedit:</b>", styles["Normal"]))
        try:
            qr_code = qr.QrCodeWidget(excel_link)
            qr_draw = Drawing(70, 70)
            qr_draw.add(qr_code)
            elems.append(Spacer(1,6))
            elems.append(qr_draw)
        except Exception as e:
            elems.append(Paragraph(f"(QR gagal dibuat: {e})", styles["Normal"]))

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# ===== Session State =====
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

# ===== Keyword config (edit sesuai SOP kamu) =====
# kata kunci start — jika status mengandung salah satu kata ini maka dianggap START
START_KEYWORDS = [
    "nor", "nor tendered", "nor accepted", "commenced loading", "commenced discharge",
    "commence loading", "commence discharge", "commenced", "commence"
]
# kata kunci stop — jika status mengandung salah satu kata ini maka dianggap STOP
STOP_KEYWORDS = [
    "completed loading", "completed discharge", "completed", "completed loading",
    "completed discharge", "depart", "departed", "departured", "departure", "moored", "finished", "finished loading"
]

# ===== Input Header =====
st.header("📥 Data Utama")
col1, col2 = st.columns(2)
with col1:
    tugboat = st.text_input("Tug Boat")
    pol = st.text_input("Port of Loading (POL)")
    shipper = st.text_input("Shipper")
with col2:
    barge = st.text_input("Barge")
    pod = st.text_input("Port of Discharge (POD)")
    laycan = st.text_input("Laycan")

col3, col4 = st.columns(2)
with col3:
    prorata = st.number_input("Prorata (Hari)", 0.0, step=0.5, value=0.0)
with col4:
    rate_per_day = st.number_input("Rate Demurrage (Rp/Hari)", 0.0, step=100000.0, value=0.0)

st.markdown("**Catatan:** Input `Status` bebas ketik. Sistem akan mencoba mendeteksi START/STOP berdasarkan kata kunci (lihat konfigurasi di kode).")
st.markdown("---")

# ===== POL Input =====
st.subheader("1️⃣ Voyage Events – POL")
if st.button("➕ Tambah Event POL"):
    st.session_state.pol_rows.append({"Date": date.today(), "Time": default_time(), "Status": ""})

new_pol = []
for i, row in enumerate(st.session_state.pol_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    c = st.columns([0.3,2,1,3,0.6])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pol_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pol_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pol_status_{i}")
    rem = c[4].button("❌", key=f"pol_del_{i}")
    if not rem:
        new_pol.append({"Date": d, "Time": t, "Status": s})
st.session_state.pol_rows = new_pol

st.markdown("---")

# ===== POD Input =====
st.subheader("2️⃣ Voyage Events – POD")
if st.button("➕ Tambah Event POD"):
    st.session_state.pod_rows.append({"Date": date.today(), "Time": default_time(), "Status": ""})

new_pod = []
for i, row in enumerate(st.session_state.pod_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    c = st.columns([0.3,2,1,3,0.6])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pod_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pod_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pod_status_{i}")
    rem = c[4].button("❌", key=f"pod_del_{i}")
    if not rem:
        new_pod.append({"Date": d, "Time": t, "Status": s})
st.session_state.pod_rows = new_pod

st.markdown("---")

# ===== Core: flexible start-stop calculation per list of rows =====
def calc_segments_and_hours(rows, start_keywords, stop_keywords):
    """
    rows: list of dict {"Date": date, "Time": time, "Status": str}
    returns:
      enriched_rows: list of dicts with added keys "Block ID" (or ""), "Duration (hrs)" (float or None)
      total_hours: sum of all segment durations
    Logic:
      - sort rows by datetime
      - iterate, when status contains any start_keyword -> mark start_time and block_id
      - when status contains any stop_keyword and start_time exists -> compute duration, close block
      - supports multiple blocks; unmatched starts ignored unless closed
      - status matching is case-insensitive and checks substring containment
    """
    if not rows:
        return [], 0.0

    # prepare sorted rows
    rows_sorted = sorted(rows, key=lambda r: safe_datetime(r["Date"], r["Time"]))
    enriched = []
    total_hours = 0.0
    start_time = None
    current_block = None
    block_counter = 0

    for r in rows_sorted:
        status = (r.get("Status") or "").strip()
        dt = safe_datetime(r["Date"], r["Time"])
        status_low = status.lower()

        is_start = any(k.lower() in status_low for k in start_keywords)
        is_stop = any(k.lower() in status_low for k in stop_keywords)

        row_copy = r.copy()
        row_copy["Block ID"] = ""
        row_copy["Duration (hrs)"] = float("nan")

        if is_start:
            # start a new block (if there is an open block, we keep it open and start new block)
            block_counter += 1
            start_time = dt
            current_block = f"B{block_counter}"
            row_copy["Block ID"] = current_block
            # mark start row (duration stays NaN)
        elif is_stop and start_time:
            # close current block
            dur = duration_hours_between(start_time, dt)
            total_hours += dur
            row_copy["Block ID"] = current_block if current_block else f"B{block_counter+1}"
            row_copy["Duration (hrs)"] = dur
            # reset
            start_time = None
            current_block = None
        else:
            # neither start nor stop: if there's an open block, mark with block id
            if current_block:
                row_copy["Block ID"] = current_block

        enriched.append(row_copy)

    # If there's an open block at end (no stop found), compute until "now"
    if start_time:
        now = datetime.now()
        dur = duration_hours_between(start_time, now)
        total_hours += dur
        # attach this duration to a synthesized row? We'll append a summary row indicating open block duration.
        enriched.append({
            "Date": now.date(),
            "Time": now.time().replace(microsecond=0),
            "Status": "OPEN BLOCK (auto-close to now)",
            "Block ID": current_block if current_block else f"B{block_counter+1}",
            "Duration (hrs)": dur
        })

    return enriched, total_hours

# ===== Tombol Calculate =====
if st.button("⚙️ Calculate Laytime"):
    # process POL
    pol_enriched, pol_hours = calc_segments_and_hours(
        st.session_state.pol_rows, START_KEYWORDS, STOP_KEYWORDS
    )
    # process POD
    pod_enriched, pod_hours = calc_segments_and_hours(
        st.session_state.pod_rows, START_KEYWORDS, STOP_KEYWORDS
    )

    total_hours = pol_hours + pod_hours
    total_days = total_hours / 24
    detention_days = max(0.0, total_days - prorata)
    total_cost = detention_days * rate_per_day

    # prepare ctx for PDF
    ctx = {
        "tugboat": tugboat, "barge": barge, "pol": pol, "pod": pod,
        "shipper": shipper, "laycan": laycan,
        "prorata": prorata, "rate_per_day": rate_per_day,
        "pol_rows": pol_enriched, "pod_rows": pod_enriched,
        "pol_hours": pol_hours, "pod_hours": pod_hours,
        "total_hours": total_hours, "total_days": total_days,
        "detention_days": detention_days, "total_cost": total_cost
    }

    # ===== Generate Excel otomatis (gabung 1 sheet) =====
    df_pol = pd.DataFrame(pol_enriched)
    df_pod = pd.DataFrame(pod_enriched)

    # Normalisasi kolom / format
    def prepare_df_for_excel(df, section_name):
        if df.empty:
            return pd.DataFrame(columns=["Section", "Date", "Time", "Status", "Block ID", "Duration (hrs)"])
        df2 = df.copy()
        df2["Date"] = df2["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df2["Time"] = df2["Time"].apply(lambda t: t.strftime("%H:%M"))
        df2.insert(0, "Section", section_name)
        # ensure Duration column present and numeric/NaN
        if "Duration (hrs)" not in df2.columns:
            df2["Duration (hrs)"] = pd.NA
        return df2[["Section", "Date", "Time", "Status", "Block ID", "Duration (hrs)"]]

    df_pol_x = prepare_df_for_excel(df_pol, "POL")
    df_pod_x = prepare_df_for_excel(df_pod, "POD")

    # Summary rows
    summary_rows = [
        ["SUMMARY", "", "", "Durasi POL", f"{pol_hours:.2f} jam ({pol_hours/24:.2f} hari)", ""],
        ["SUMMARY", "", "", "Durasi POD", f"{pod_hours:.2f} jam ({pod_hours/24:.2f} hari)", ""],
        ["SUMMARY", "", "", "Total (POL+POD)", f"{total_hours:.2f} jam ({total_days:.2f} hari)", ""],
        ["SUMMARY", "", "", "Prorata (Free Time)", f"{prorata:.2f} hari", "" , ""],
        ["SUMMARY", "", "", "Demurrage Days", f"{detention_days:.2f} hari", "" , ""],
        ["SUMMARY", "", "", "Total Biaya", format_rp(total_cost), "" , ""],
    ]
    # convert to DataFrame with matching columns (we'll put summary in same sheet but with different layout)
    df_summary = pd.DataFrame(summary_rows, columns=["Section", "Date", "Time", "Status", "Duration (hrs)", "Block ID"])

    # combine: we'll align columns by creating a unified frame
    combined = pd.concat([df_pol_x, df_pod_x], ignore_index=True, sort=False)

    # create Excel buffer
    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        combined.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=0)
        # write summary below with some spacing
        start_summary_row = len(combined) + 2
        df_summary.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=start_summary_row)

        workbook = writer.book
        worksheet = writer.sheets["LAYTIME_REPORT"]

        # format header
        header_fmt = workbook.add_format({
            "bold": True, "align": "center", "bg_color": "#DCE6F1", "border": 1
        })
        for col_num, value in enumerate(combined.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 20)

        # bold for summary headers
        bold = workbook.add_format({"bold": True})
        worksheet.write(start_summary_row, 0, "SUMMARY", bold)

    excel_buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Laytime_Report_{timestamp}.xlsx"

    st.session_state.excel_data = excel_buf.getvalue()
    st.session_state.excel_filename = excel_filename

    excel_link = f"{excel_filename}"  # ganti ke URL publik bila deploy
    pdf_data = build_pdf(ctx, excel_link=excel_link)
    st.session_state.pdf_data = pdf_data
    st.session_state.calc_done = True
    st.session_state.ctx = ctx

# ===== Output =====
if st.session_state.calc_done:
    ctx = st.session_state.ctx
    st.subheader("📊 Hasil Perhitungan")
    st.write(f"POL Duration: **{ctx['pol_hours']:.2f} jam** ({ctx['pol_hours']/24:.2f} hari)")
    st.write(f"POD Duration: **{ctx['pod_hours']:.2f} jam** ({ctx['pod_hours']/24:.2f} hari)")
    st.write(f"Total Duration: **{ctx['total_hours']:.2f} jam** ({ctx['total_days']:.2f} hari)")
    st.write(f"Free Time (Prorata): {ctx['prorata']:.2f} hari")
    st.write(f"Demurrage Days: **{ctx['detention_days']:.2f} hari**")
    st.write(f"Total Demurrage: **{format_rp(ctx['total_cost'])}**")

    st.markdown("### Sample event table (lihat Excel untuk detail kolom Block ID dan Duration)")
    st.dataframe(pd.concat([pd.DataFrame(ctx["pol_rows"]), pd.DataFrame(ctx["pod_rows"])], ignore_index=True))

    st.download_button("📄 Download PDF", st.session_state.pdf_data, "Laytime_Report.pdf", "application/pdf")
    st.download_button("📊 Download Excel (1 Sheet)", st.session_state.excel_data, st.session_state.excel_filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
