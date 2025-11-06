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
st.title("⚓ Voyage Report – Detention / Demurrage Calculator")

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

# ===== PDF Builder =====
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
        data = [["No", "Date", "Time", "Status"]]
        for i, r in enumerate(rows, start=1):
            data.append([
                str(i),
                r["Date"].strftime("%d %b %Y"),
                r["Time"].strftime("%H:%M"),
                r["Status"]
            ])
        t = Table(data, colWidths=[30, 100, 60, 310])
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

# ===== Tombol Calculate =====
if st.button("⚙️ Calculate Laytime"):
    def calc_hours(rows):
        if not rows:
            return 0
        dts = [safe_datetime(r["Date"], r["Time"]) for r in rows]
        dts.sort()
        return duration_hours_between(dts[0], dts[-1])

    pol_hours = calc_hours(st.session_state.pol_rows)
    pod_hours = calc_hours(st.session_state.pod_rows)
    total_hours = pol_hours + pod_hours
    total_days = total_hours / 24
    detention_days = max(0.0, total_days - prorata)
    total_cost = detention_days * rate_per_day

    ctx = {
        "tugboat": tugboat, "barge": barge, "pol": pol, "pod": pod,
        "shipper": shipper, "laycan": laycan,
        "prorata": prorata, "rate_per_day": rate_per_day,
        "pol_rows": st.session_state.pol_rows, "pod_rows": st.session_state.pod_rows,
        "pol_hours": pol_hours, "pod_hours": pod_hours,
        "total_hours": total_hours, "total_days": total_days,
        "detention_days": detention_days, "total_cost": total_cost
    }

    # ===== Generate Excel otomatis (POL + POD + Summary di 1 sheet) =====
    df_pol = pd.DataFrame(ctx["pol_rows"])
    df_pod = pd.DataFrame(ctx["pod_rows"])

    if not df_pol.empty:
        df_pol["Date"] = df_pol["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df_pol["Time"] = df_pol["Time"].apply(lambda t: t.strftime("%H:%M"))
        df_pol.insert(0, "Section", "POL")
    else:
        df_pol = pd.DataFrame(columns=["Section", "Date", "Time", "Status"])

    if not df_pod.empty:
        df_pod["Date"] = df_pod["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
        df_pod["Time"] = df_pod["Time"].apply(lambda t: t.strftime("%H:%M"))
        df_pod.insert(0, "Section", "POD")
    else:
        df_pod = pd.DataFrame(columns=["Section", "Date", "Time", "Status"])

    summary_rows = [
        ["SUMMARY", "Durasi POL", f"{ctx['pol_hours']:.2f} jam ({ctx['pol_hours']/24:.2f} hari)", ""],
        ["SUMMARY", "Durasi POD", f"{ctx['pod_hours']:.2f} jam ({ctx['pod_hours']/24:.2f} hari)", ""],
        ["SUMMARY", "Total", f"{ctx['total_hours']:.2f} jam ({ctx['total_days']:.2f} hari)", ""],
        ["SUMMARY", "Prorata (Free Time)", f"{ctx['prorata']:.2f} hari", ""],
        ["SUMMARY", "Demurrage Days", f"{ctx['detention_days']:.2f} hari", ""],
        ["SUMMARY", "Total Biaya", format_rp(ctx['total_cost']), ""],
    ]
    df_summary = pd.DataFrame(summary_rows, columns=["Section", "Date", "Time", "Status"])

    combined_df = pd.concat([df_pol, df_pod, df_summary], ignore_index=True)

    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="LAYTIME_REPORT")
        workbook = writer.book
        worksheet = writer.sheets["LAYTIME_REPORT"]
        header_fmt = workbook.add_format({
            "bold": True, "align": "center", "bg_color": "#DCE6F1", "border": 1
        })
        for col_num, value in enumerate(combined_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 20)

    excel_buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Laytime_Report_{timestamp}.xlsx"

    st.session_state.excel_data = excel_buf.getvalue()
    st.session_state.excel_filename = excel_filename

    excel_link = f"{excel_filename}"  # bisa diganti ke URL publik pas deploy
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

    st.download_button("📄 Download PDF", st.session_state.pdf_data, "Laytime_Report.pdf", "application/pdf")
    st.download_button("📊 Download Excel (1 Sheet)", st.session_state.excel_data, st.session_state.excel_filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
