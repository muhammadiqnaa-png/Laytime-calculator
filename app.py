# laytime_app_manual_start_stop.py
import streamlit as st
from datetime import datetime, date, time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
import pandas as pd

st.set_page_config(page_title="⚓ Laytime Manual Start/Stop", layout="wide")
st.title("⚓ Laytime Calculator — Manual Start / Stop")

# ---------------- Helpers ----------------
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

# ---------------- PDF builder (slim) ----------------
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
        data = [["No", "Date", "Time", "Status", "Start", "Stop", "Block ID", "Duration (hrs)"]]
        for i, r in enumerate(rows, start=1):
            start_flag = "✓" if r.get("Start") else ""
            stop_flag = "✓" if r.get("Stop") else ""
            dur = "" if pd.isna(r.get("Duration (hrs)")) else f"{r.get('Duration (hrs)'):.2f}"
            data.append([
                str(i),
                r["Date"].strftime("%d %b %Y"),
                r["Time"].strftime("%H:%M"),
                r["Status"],
                start_flag, stop_flag,
                r.get("Block ID", ""),
                dur
            ])
        t = Table(data, colWidths=[30, 100, 60, 200, 35, 35, 60, 60])
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

# ---------------- Session state init ----------------
for k in ["pol_rows", "pod_rows", "calc_done", "pdf_data", "excel_data", "excel_filename", "ctx"]:
    if k not in st.session_state:
        if k in ("pol_rows", "pod_rows"):
            st.session_state[k] = []
        else:
            st.session_state[k] = None
st.session_state.calc_done = bool(st.session_state.calc_done)

# ---------------- UI: Header ----------------
st.header("📥 Data Utama")
col1, col2 = st.columns(2)
with col1:
    tugboat = st.text_input("Tug Boat", value=st.session_state.get("tugboat",""))
    pol = st.text_input("Port of Loading (POL)", value=st.session_state.get("pol",""))
    shipper = st.text_input("Shipper", value=st.session_state.get("shipper",""))
with col2:
    barge = st.text_input("Barge", value=st.session_state.get("barge",""))
    pod = st.text_input("Port of Discharge (POD)", value=st.session_state.get("pod",""))
    laycan = st.text_input("Laycan", value=st.session_state.get("laycan",""))

col3, col4 = st.columns(2)
with col3:
    prorata = st.number_input("Prorata (Hari)", 0.0, step=0.5, value=st.session_state.get("prorata", 0.0))
with col4:
    rate_per_day = st.number_input("Rate Demurrage (Rp/Hari)", 0.0, step=100000.0, value=st.session_state.get("rate_per_day", 0.0))

st.markdown("**Catatan:** Isi `Status` bebas ketik. Tandai kolom `Start` / `Stop` di kanan supaya perhitungan pakai pairing manual.")
st.markdown("---")

# ---------------- POL Input (manual rows with Start/Stop) ----------------
st.subheader("1️⃣ Voyage Events – POL")
if st.button("➕ Tambah Event POL"):
    st.session_state.pol_rows.append({"Date": date.today(), "Time": default_time(), "Status": "", "Start": False, "Stop": False})

new_pol = []
for i, row in enumerate(st.session_state.pol_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    row.setdefault("Start", False)
    row.setdefault("Stop", False)

    c = st.columns([0.3,2,1,3,0.6,0.5,0.5])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pol_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pol_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pol_status_{i}")
    rem = c[4].button("❌", key=f"pol_del_{i}")
    # Start / Stop checkboxes at right
    st_start = c[5].checkbox("Start", value=row.get("Start", False), key=f"pol_start_{i}")
    st_stop = c[6].checkbox("Stop", value=row.get("Stop", False), key=f"pol_stop_{i}")

    if not rem:
        new_pol.append({"Date": d, "Time": t, "Status": s, "Start": st_start, "Stop": st_stop})
st.session_state.pol_rows = new_pol

st.markdown("---")

# ---------------- POD Input ----------------
st.subheader("2️⃣ Voyage Events – POD")
if st.button("➕ Tambah Event POD"):
    st.session_state.pod_rows.append({"Date": date.today(), "Time": default_time(), "Status": "", "Start": False, "Stop": False})

new_pod = []
for i, row in enumerate(st.session_state.pod_rows):
    row.setdefault("Date", date.today())
    row.setdefault("Time", default_time())
    row.setdefault("Status", "")
    row.setdefault("Start", False)
    row.setdefault("Stop", False)

    c = st.columns([0.3,2,1,3,0.6,0.5,0.5])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pod_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pod_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pod_status_{i}")
    rem = c[4].button("❌", key=f"pod_del_{i}")
    st_start = c[5].checkbox("Start", value=row.get("Start", False), key=f"pod_start_{i}")
    st_stop = c[6].checkbox("Stop", value=row.get("Stop", False), key=f"pod_stop_{i}")

    if not rem:
        new_pod.append({"Date": d, "Time": t, "Status": s, "Start": st_start, "Stop": st_stop})
st.session_state.pod_rows = new_pod

st.markdown("---")

# ---------------- Option: auto-close open start to now? ----------------
auto_close = st.checkbox("Auto-close any open Start to NOW when calculating (if a Start has no Stop)", value=False)

# ---------------- Core pairing logic ----------------
def pair_and_calc(rows, auto_close=False):
    """
    rows: list of dict with keys Date, Time, Status, Start(bool), Stop(bool)
    returns enriched_rows, total_hours (sum of paired durations)
    enriched_rows: each row gains keys Block ID (str or ""), Duration (hrs) for stop rows
    Pairing rule:
      - sort by datetime
      - iterate: when Start==True -> open new block (B1, B2,..)
      - when Stop==True and a block open -> close that block, compute duration
      - if Stop==True but no open block -> ignored (or assigned)
      - if multiple Start without Stop: multiple opens stacked; we pair in FIFO (first Start paired with first subsequent Stop)
    """
    if not rows:
        return [], 0.0

    # sort
    sorted_rows = sorted(rows, key=lambda r: safe_datetime(r["Date"], r["Time"]))
    enriched = []
    block_queue = []  # list of dicts: {"id": "B1", "start_time": dt}
    block_counter = 0
    total = 0.0

    for r in sorted_rows:
        row = r.copy()
        row["Block ID"] = ""
        row["Duration (hrs)"] = float("nan")
        dt = safe_datetime(row["Date"], row["Time"])

        # If this row marked as Start -> push to queue
        if row.get("Start"):
            block_counter += 1
            block_id = f"B{block_counter}"
            block_queue.append({"id": block_id, "start_time": dt})
            row["Block ID"] = block_id
            # duration remains NaN for start row

        # If this row marked as Stop -> pop earliest open block and close
        if row.get("Stop"):
            if block_queue:
                b = block_queue.pop(0)  # FIFO pairing
                dur = duration_hours_between(b["start_time"], dt)
                total += dur
                row["Block ID"] = b["id"]
                row["Duration (hrs)"] = dur
            else:
                # no open block to match: we leave Block ID empty and Duration NaN
                row["Block ID"] = ""
                row["Duration (hrs)"] = float("nan")

        enriched.append(row)

    # handle any remaining open blocks
    if block_queue:
        if auto_close:
            now = datetime.now()
            for b in block_queue:
                dur = duration_hours_between(b["start_time"], now)
                total += dur
                # append a synthetic row to indicate auto-close
                enriched.append({
                    "Date": now.date(),
                    "Time": now.time().replace(microsecond=0),
                    "Status": "AUTO-CLOSE (to NOW)",
                    "Start": False,
                    "Stop": True,
                    "Block ID": b["id"],
                    "Duration (hrs)": dur
                })
        else:
            # we will NOT auto-close: leave as open (no added duration)
            pass

    return enriched, total

# ---------------- Calculate button ----------------
if st.button("⚙️ Calculate Laytime"):
    pol_enriched, pol_hours = pair_and_calc(st.session_state.pol_rows, auto_close=auto_close)
    pod_enriched, pod_hours = pair_and_calc(st.session_state.pod_rows, auto_close=auto_close)

    total_hours = pol_hours + pod_hours
    total_days = total_hours / 24
    detention_days = max(0.0, total_days - prorata)
    total_cost = detention_days * rate_per_day

    # prepare ctx
    ctx = {
        "tugboat": tugboat, "barge": barge, "pol": pol, "pod": pod,
        "shipper": shipper, "laycan": laycan,
        "prorata": prorata, "rate_per_day": rate_per_day,
        "pol_rows": pol_enriched, "pod_rows": pod_enriched,
        "pol_hours": pol_hours, "pod_hours": pod_hours,
        "total_hours": total_hours, "total_days": total_days,
        "detention_days": detention_days, "total_cost": total_cost
    }

    # ---------------- Build single-sheet Excel ----------------
    def prepare_df(rows, section_name):
        if not rows:
            return pd.DataFrame(columns=["Section","Date","Time","Status","Start","Stop","Block ID","Duration (hrs)"])
        df = pd.DataFrame(rows).copy()
        # convert booleans to check marks for excel readability
        df["Start"] = df.get("Start", False).apply(lambda x: "✓" if x else "")
        df["Stop"] = df.get("Stop", False).apply(lambda x: "✓" if x else "")
        # ensure Date/Time formatting
        df["Date"] = df["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df["Time"] = df["Time"].apply(lambda t: t.strftime("%H:%M"))
        # ensure Duration numeric or empty
        if "Duration (hrs)" in df.columns:
            df["Duration (hrs)"] = df["Duration (hrs)"].apply(lambda v: round(v,2) if pd.notna(v) else "")
        else:
            df["Duration (hrs)"] = ""
        df.insert(0, "Section", section_name)
        # reorder
        return df[["Section","Date","Time","Status","Start","Stop","Block ID","Duration (hrs)"]]

    df_pol_x = prepare_df(pol_enriched, "POL")
    df_pod_x = prepare_df(pod_enriched, "POD")

    combined = pd.concat([df_pol_x, df_pod_x], ignore_index=True, sort=False)

    # summary rows as a small table appended below
    summary_rows = [
        ["SUMMARY", "", "", "Durasi POL", f"{pol_hours:.2f} jam ({pol_hours/24:.2f} hari)", "", "", ""],
        ["SUMMARY", "", "", "Durasi POD", f"{pod_hours:.2f} jam ({pod_hours/24:.2f} hari)", "", "", ""],
        ["SUMMARY", "", "", "Total (POL+POD)", f"{total_hours:.2f} jam ({total_days:.2f} hari)", "", "", ""],
        ["SUMMARY", "", "", "Prorata (Free Time)", f"{prorata:.2f} hari", "", "", ""],
        ["SUMMARY", "", "", "Demurrage Days", f"{detention_days:.2f} hari", "", "", ""],
        ["SUMMARY", "", "", "Total Biaya", format_rp(total_cost), "", "", ""],
    ]
    df_summary = pd.DataFrame(summary_rows, columns=combined.columns)

    # write excel
    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        combined.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=0)
        start_summary_row = len(combined) + 2
        df_summary.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT", startrow=start_summary_row)
        workbook = writer.book
        worksheet = writer.sheets["LAYTIME_REPORT"]

        header_fmt = workbook.add_format({"bold": True, "align": "center", "bg_color": "#DCE6F1", "border": 1})
        for col_num, value in enumerate(combined.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 18)

        # bold summary label
        bold = workbook.add_format({"bold": True})
        worksheet.write(start_summary_row, 0, "SUMMARY", bold)

    excel_buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Laytime_Report_{timestamp}.xlsx"

    st.session_state.excel_data = excel_buf.getvalue()
    st.session_state.excel_filename = excel_filename

    excel_link = excel_filename  # replace with public URL when deployed
    pdf_data = build_pdf(ctx, excel_link=excel_link)
    st.session_state.pdf_data = pdf_data
    st.session_state.calc_done = True
    st.session_state.ctx = ctx

# ---------------- Output ----------------
if st.session_state.calc_done:
    ctx = st.session_state.ctx
    st.subheader("📊 Hasil Perhitungan")
    st.write(f"POL Duration: **{ctx['pol_hours']:.2f} jam** ({ctx['pol_hours']/24:.2f} hari)")
    st.write(f"POD Duration: **{ctx['pod_hours']:.2f} jam** ({ctx['pod_hours']/24:.2f} hari)")
    st.write(f"Total Duration: **{ctx['total_hours']:.2f} jam** ({ctx['total_days']:.2f} hari)")
    st.write(f"Free Time (Prorata): {ctx['prorata']:.2f} hari")
    st.write(f"Demurrage Days: **{ctx['detention_days']:.2f} hari**")
    st.write(f"Total Demurrage: **{format_rp(ctx['total_cost'])}**")

    st.markdown("### Sample event table (lihat Excel untuk Block ID & Duration detail)")
    # show a nice combined dataframe preview
    df_view = pd.concat([pd.DataFrame(ctx["pol_rows"]), pd.DataFrame(ctx["pod_rows"])], ignore_index=True, sort=False)
    # convert booleans to ticks for display
    if not df_view.empty:
        if "Start" in df_view.columns:
            df_view["Start"] = df_view["Start"].apply(lambda x: "✓" if x else "")
        if "Stop" in df_view.columns:
            df_view["Stop"] = df_view["Stop"].apply(lambda x: "✓" if x else "")
    st.dataframe(df_view.reset_index(drop=True))

    st.download_button("📄 Download PDF", st.session_state.pdf_data, "Laytime_Report.pdf", "application/pdf")
    st.download_button("📊 Download Excel (1 Sheet)", st.session_state.excel_data, st.session_state.excel_filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
