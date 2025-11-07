import streamlit as st
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd

st.set_page_config(page_title="⚓ Voyage Report", layout="wide")
st.title("⚓ Voyage Report – Laytime Calculator")

# ===== Helper =====
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

# ===== PDF Builder =====
def build_pdf(ctx):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=8, spaceAfter=6, textColor=colors.darkblue))
    elems = []

    elems.append(Paragraph("⚓ VOYAGE REPORT – LAYTIME CALCULATION", styles["CenterTitle"]))

    info = [
        ["Tug Boat", ctx.get("tugboat","")],
        ["Barge", ctx.get("barge","")],
        ["POL", ctx.get("pol","")],
        ["POD", ctx.get("pod","")],
        ["Shipper", ctx.get("shipper","")],
        ["Laycan", ctx.get("laycan","")],
        ["Free Time", f"{ctx['prorata']:.2f} Hari"],
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
        data = [["No", "Date", "Time", "Status", "Duration (Hours)"]]
        for i, r in enumerate(rows, start=1):
            data.append([
                str(i),
                r["Date"].strftime("%d %b %Y"),
                r["Time"].strftime("%H:%M"),
                r["Status"],
                f"{r['Duration']:.2f}" if "Duration" in r else "-"
            ])
        t = Table(data, colWidths=[30, 90, 60, 280, 90])
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
        ["Free Time", f"{ctx['prorata']:.2f} hari"],
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

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# ===== Session =====
if "pol_rows" not in st.session_state:
    st.session_state.pol_rows = []
if "pod_rows" not in st.session_state:
    st.session_state.pod_rows = []

# ===== Input Data Utama =====
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
    prorata = st.number_input("Free Time (Hari)", 0.0, step=0.5, value=0.0)
with col4:
    rate_per_day = st.number_input("Rate Demurrage (Rp/Hari)", 0.0, step=100000.0, value=0.0)

st.markdown("---")

# ===== Input POL =====
st.subheader("1️⃣ Voyage Events – POL")
if st.button("➕ Tambah Event POL"):
    st.session_state.pol_rows.append({"Date": date.today(), "Time": default_time(), "Status": "", "Duration": 0.0})

new_pol = []
for i, row in enumerate(st.session_state.pol_rows):
    c = st.columns([0.2, 2, 1, 2, 1])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pol_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pol_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pol_status_{i}")
    rem = c[4].button("❌", key=f"pol_del_{i}")
    if not rem:
        new_pol.append({"Date": d, "Time": t, "Status": s})
st.session_state.pol_rows = new_pol

st.markdown("---")

# ===== Input POD =====
st.subheader("2️⃣ Voyage Events – POD")
if st.button("➕ Tambah Event POD"):
    st.session_state.pod_rows.append({"Date": date.today(), "Time": default_time(), "Status": "", "Duration": 0.0})

new_pod = []
for i, row in enumerate(st.session_state.pod_rows):
    c = st.columns([0.2, 2, 1, 2, 1])
    c[0].markdown(f"**{i+1}**")
    d = c[1].date_input("", row["Date"], key=f"pod_date_{i}")
    t = c[2].time_input("", row["Time"], key=f"pod_time_{i}")
    s = c[3].text_input("", row["Status"], key=f"pod_status_{i}")
    rem = c[4].button("❌", key=f"pod_del_{i}")
    if not rem:
        new_pod.append({"Date": d, "Time": t, "Status": s})
st.session_state.pod_rows = new_pod

st.markdown("---")

# ===== Hitung Laytime =====
if st.button("⚙️ Calculate Laytime"):
    def calc_rows(rows):
        if len(rows) < 2:
            return rows, 0.0
        total = 0.0
        updated = []
        dts = [safe_datetime(r["Date"], r["Time"]) for r in rows]
        for i in range(len(rows)):
            dur = 0.0
            if i > 0:
                dur = duration_hours_between(dts[i-1], dts[i])
                total += dur
            updated.append({
                "Date": rows[i]["Date"],
                "Time": rows[i]["Time"],
                "Status": rows[i]["Status"],
                "Duration": dur
            })
        return updated, total

    pol_rows, pol_hours = calc_rows(st.session_state.pol_rows)
    pod_rows, pod_hours = calc_rows(st.session_state.pod_rows)
    total_hours = pol_hours + pod_hours
    total_days = total_hours / 24
    detention_days = max(0.0, total_days - prorata)
    total_cost = detention_days * rate_per_day

    ctx = {
        "tugboat": tugboat, "barge": barge, "pol": pol, "pod": pod,
        "shipper": shipper, "laycan": laycan,
        "prorata": prorata, "rate_per_day": rate_per_day,
        "pol_rows": pol_rows, "pod_rows": pod_rows,
        "pol_hours": pol_hours, "pod_hours": pod_hours,
        "total_hours": total_hours, "total_days": total_days,
        "detention_days": detention_days, "total_cost": total_cost
    }

    # Excel (1 sheet gabungan)
    df_pol = pd.DataFrame(pol_rows)
    df_pod = pd.DataFrame(pod_rows)
    df_pol["Section"] = "POL"
    df_pod["Section"] = "POD"
    df_all = pd.concat([df_pol, df_pod])
    df_all = df_all[["Section", "Date", "Time", "Status", "Duration"]]

    summary_df = pd.DataFrame({
        "Parameter": ["Durasi POL (jam)", "Durasi POD (jam)", "Total Jam", "Total Hari", "Free Time (hari)", "Demurrage Days", "Total Biaya (Rp)"],
        "Nilai": [pol_hours, pod_hours, total_hours, total_days, prorata, detention_days, total_cost]
    })

    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        df_all.to_excel(writer, index=False, sheet_name="Laytime Data")
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
    excel_buf.seek(0)

    pdf_data = build_pdf(ctx)

    # Output
    st.subheader("📊 Hasil Perhitungan")
    st.write(f"POL Duration: **{pol_hours:.2f} jam** ({pol_hours/24:.2f} hari)")
    st.write(f"POD Duration: **{pod_hours:.2f} jam** ({pod_hours/24:.2f} hari)")
    st.write(f"Total Duration: **{total_hours:.2f} jam** ({total_days:.2f} hari)")
    st.write(f"Free Time (Prorata): {prorata:.2f} hari")
    st.write(f"Demurrage Days: **{detention_days:.2f} hari**")
    st.write(f"Total Demurrage: **{format_rp(total_cost)}**")

    st.download_button("📄 Download PDF", pdf_data, "Laytime_Report.pdf", "application/pdf")
    st.download_button("📊 Download Excel", excel_buf, "Laytime_Report.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
