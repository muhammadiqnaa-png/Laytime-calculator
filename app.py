# app.py
import streamlit as st
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="⚓ Voyage Report – Detention/Demurrage", layout="wide")
st.title("⚓ Voyage Report – Barge Detention/Demurrage Calculator")

# -------------------------
# Helper functions
# -------------------------
def default_time():
    return datetime.now().time().replace(second=0, microsecond=0)

def format_rp(x):
    try:
        return "Rp {:,}".format(int(round(x))).replace(",", ".")
    except:
        return f"Rp {x}"

def row_duration_hours(row):
    """
    row: dict with keys Date (date), From (time), To (time)
    returns duration in hours (float), handles To < From by adding 24h
    """
    try:
        dt_from = datetime.combine(row["Date"], row["From"])
        dt_to = datetime.combine(row["Date"], row["To"])
        if dt_to < dt_from:
            dt_to += timedelta(days=1)
        dur_hours = (dt_to - dt_from).total_seconds() / 3600.0
        return dur_hours
    except Exception:
        return 0.0

def build_pdf_bytes(context):
    """
    context: dict containing all values needed for PDF
    returns: bytes
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=8, spaceAfter=6, textColor=colors.darkblue))

    elems = []
    elems.append(Paragraph("⚓ VOYAGE REPORT – DETENTION / DEMURRAGE", styles["CenterTitle"]))
    elems.append(Spacer(1, 6))

    # Info section
    elems.append(Paragraph("<b>Informasi Umum</b>", styles["SubHeader"]))
    info_table = [
        ["Tug Boat", context["tug_boat"]],
        ["Barge", context["barge"]],
        ["Port of Loading (POL)", context["pol"]],
        ["Port of Discharge (POD)", context["pod"]],
        ["Shipper", context["shipper"]],
        ["Laycan", context["laycan"]],
        ["Prorata (Free Time)", f"{context['prorata_days']:.2f} Hari"],
        ["Rate Demurrage", f"{format_rp(context['rate_demurrage'])} / Hari"],
    ]
    t_info = Table(info_table, colWidths=[160, 340])
    t_info.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))
    elems.append(t_info)
    elems.append(Spacer(1, 8))

    # Voyage report POL
    elems.append(Paragraph("<b>Voyage Activity – POL</b>", styles["SubHeader"]))
    pol_rows = [["No", "Date", "From", "To", "Status", "Durasi (Jam)"]]
    for i, r in enumerate(context["pol_rows"], start=1):
        pol_rows.append([
            str(i),
            r["Date"].strftime("%d %b %Y"),
            r["From"].strftime("%H:%M"),
            r["To"].strftime("%H:%M"),
            r["Status"],
            f"{r['Duration']:.2f}"
        ])
    t_pol = Table(pol_rows, colWidths=[30, 90, 60, 60, 200, 60])
    t_pol.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(t_pol)
    elems.append(Spacer(1, 6))

    # Voyage report POD
    elems.append(Paragraph("<b>Voyage Activity – POD</b>", styles["SubHeader"]))
    pod_rows = [["No", "Date", "From", "To", "Status", "Durasi (Jam)"]]
    for i, r in enumerate(context["pod_rows"], start=1):
        pod_rows.append([
            str(i),
            r["Date"].strftime("%d %b %Y"),
            r["From"].strftime("%H:%M"),
            r["To"].strftime("%H:%M"),
            r["Status"],
            f"{r['Duration']:.2f}"
        ])
    t_pod = Table(pod_rows, colWidths=[30, 90, 60, 60, 200, 60])
    t_pod.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(t_pod)
    elems.append(Spacer(1, 8))

    # Summary
    elems.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
    summary = [
        ["Durasi POL", f"{context['total_pol_hours']:.2f} Jam ({context['total_pol_hours']/24:.2f} Hari)"],
        ["Durasi POD", f"{context['total_pod_hours']:.2f} Jam ({context['total_pod_hours']/24:.2f} Hari)"],
        ["Total Durasi (POL+POD)", f"{context['total_hours']:.2f} Jam ({context['total_days']:.2f} Hari)"],
        ["Free Time (Prorata)", f"{context['prorata_days']:.2f} Hari"],
        ["Detention / Demurrage Days", f"{context['detention_days']:.2f} Hari"],
        ["Total Biaya Demurrage", f"{format_rp(context['total_cost'])}"],
    ]
    t_sum = Table(summary, colWidths=[220, 280])
    t_sum.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,5), (-1,5), colors.whitesmoke),
        ("TEXTCOLOR", (0,5), (-1,5), colors.red),
    ]))
    elems.append(t_sum)

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# -------------------------
# Inputs (header)
# -------------------------
st.markdown("## 📥 Input Data Utama")
col1, col2 = st.columns(2)
with col1:
    tug_boat = st.text_input("Tug Boat")
    pol = st.text_input("Port of Loading (POL)")
    shipper = st.text_input("Shipper")
with col2:
    barge = st.text_input("Barge")
    pod = st.text_input("Port of Discharge (POD)")
    laycan = st.text_input("Laycan (contoh: 20–22 Oct 2025)")

col3, col4 = st.columns(2)
with col3:
    prorata_days = st.number_input("Prorata (Free Time – Hari)", min_value=0.0, step=0.5, value=0.0)
with col4:
    rate_demurrage = st.number_input("Rate Demurrage (Rp/Hari)", min_value=0.0, step=100000.0, value=0.0, format="%.0f")

st.markdown("---")

# -------------------------
# Initialize session state lists for rows
# -------------------------
if "pol_rows" not in st.session_state:
    st.session_state.pol_rows = [
        {"Date": date.today(), "From": default_time(), "To": default_time(), "Status": "Arrival / NOR"}
    ]
if "pod_rows" not in st.session_state:
    st.session_state.pod_rows = [
        {"Date": date.today(), "From": default_time(), "To": default_time(), "Status": "Arrival / NOR"}
    ]

# -------------------------
# POL section (voyage-style)
# -------------------------
st.markdown("## 1️⃣ Port of Loading (POL) — Voyage Events")

def pol_add_row():
    st.session_state.pol_rows.append({"Date": date.today(), "From": default_time(), "To": default_time(), "Status": ""})

def pol_remove_row(idx):
    if 0 <= idx < len(st.session_state.pol_rows):
        st.session_state.pol_rows.pop(idx)

pol_col1, pol_col2 = st.columns([3,1])
with pol_col1:
    st.write("Isi event POL: tanggal, jam from/to, dan status (keterangan).")
with pol_col2:
    st.button("➕ Tambah Baris POL", on_click=pol_add_row)

# Render POL rows
for i, row in enumerate(st.session_state.pol_rows):
    cols = st.columns([1,2,1,1,3,0.6])
    cols[0].markdown(f"**{i+1}**")
    # Date
    st_key_date = f"pol_date_{i}"
    st.session_state.setdefault(st_key_date, row["Date"])
    st.session_state[st_key_date] = cols[1].date_input("Date", value=st.session_state[st_key_date], key=st_key_date)
    # From
    st_key_from = f"pol_from_{i}"
    st.session_state.setdefault(st_key_from, row["From"])
    st.session_state[st_key_from] = cols[2].time_input("From (HH:MM)", value=st.session_state[st_key_from], key=st_key_from, step=60)
    # To
    st_key_to = f"pol_to_{i}"
    st.session_state.setdefault(st_key_to, row["To"])
    st.session_state[st_key_to] = cols[3].time_input("To (HH:MM)", value=st.session_state[st_key_to], key=st_key_to, step=60)
    # Status
    st_key_status = f"pol_status_{i}"
    st.session_state.setdefault(st_key_status, row["Status"])
    st.session_state[st_key_status] = cols[4].text_input("Status", value=st.session_state[st_key_status], key=st_key_status)
    # Remove button
    remove_btn = cols[5].button("❌", key=f"pol_remove_{i}")
    if remove_btn:
        pol_remove_row(i)
        st.experimental_rerun()

# -------------------------
# POD section (voyage-style)
# -------------------------
st.markdown("## 2️⃣ Port of Discharge (POD) — Voyage Events")

def pod_add_row():
    st.session_state.pod_rows.append({"Date": date.today(), "From": default_time(), "To": default_time(), "Status": ""})

def pod_remove_row(idx):
    if 0 <= idx < len(st.session_state.pod_rows):
        st.session_state.pod_rows.pop(idx)

pod_col1, pod_col2 = st.columns([3,1])
with pod_col1:
    st.write("Isi event POD: tanggal, jam from/to, dan status (keterangan).")
with pod_col2:
    st.button("➕ Tambah Baris POD", on_click=pod_add_row)

# Render POD rows
for i, row in enumerate(st.session_state.pod_rows):
    cols = st.columns([1,2,1,1,3,0.6])
    cols[0].markdown(f"**{i+1}**")
    # Date
    st_key_date = f"pod_date_{i}"
    st.session_state.setdefault(st_key_date, row["Date"])
    st.session_state[st_key_date] = cols[1].date_input("Date", value=st.session_state[st_key_date], key=st_key_date)
    # From
    st_key_from = f"pod_from_{i}"
    st.session_state.setdefault(st_key_from, row["From"])
    st.session_state[st_key_from] = cols[2].time_input("From (HH:MM)", value=st.session_state[st_key_from], key=st_key_from, step=60)
    # To
    st_key_to = f"pod_to_{i}"
    st.session_state.setdefault(st_key_to, row["To"])
    st.session_state[st_key_to] = cols[3].time_input("To (HH:MM)", value=st.session_state[st_key_to], key=st_key_to, step=60)
    # Status
    st_key_status = f"pod_status_{i}"
    st.session_state.setdefault(st_key_status, row["Status"])
    st.session_state[st_key_status] = cols[4].text_input("Status", value=st.session_state[st_key_status], key=st_key_status)
    # Remove button
    remove_btn = cols[5].button("❌", key=f"pod_remove_{i}")
    if remove_btn:
        pod_remove_row(i)
        st.experimental_rerun()

st.markdown("---")

# -------------------------
# Compute & Result
# -------------------------
if st.button("🚢 Hitung Detention / Demurrage", use_container_width=True):
    # Gather current rows into structured lists
    pol_rows = []
    for i in range(len(st.session_state.pol_rows)):
        row = {
            "Date": st.session_state.get(f"pol_date_{i}", date.today()),
            "From": st.session_state.get(f"pol_from_{i}", default_time()),
            "To": st.session_state.get(f"pol_to_{i}", default_time()),
            "Status": st.session_state.get(f"pol_status_{i}", "")
        }
        duration = row_duration_hours(row)
        row["Duration"] = duration
        pol_rows.append(row)

    pod_rows = []
    for i in range(len(st.session_state.pod_rows)):
        row = {
            "Date": st.session_state.get(f"pod_date_{i}", date.today()),
            "From": st.session_state.get(f"pod_from_{i}", default_time()),
            "To": st.session_state.get(f"pod_to_{i}", default_time()),
            "Status": st.session_state.get(f"pod_status_{i}", "")
        }
        duration = row_duration_hours(row)
        row["Duration"] = duration
        pod_rows.append(row)

    # Totals
    total_pol_hours = sum(r["Duration"] for r in pol_rows)
    total_pod_hours = sum(r["Duration"] for r in pod_rows)
    total_hours = total_pol_hours + total_pod_hours
    total_days = total_hours / 24.0
    detention_days = max(0.0, total_days - prorata_days)
    total_cost = detention_days * rate_demurrage

    # Show results
    st.markdown("## 📊 Hasil Perhitungan")
    st.write(f"- Durasi POL: **{total_pol_hours:.2f} jam** ({total_pol_hours/24:.2f} hari)")
    st.write(f"- Durasi POD: **{total_pod_hours:.2f} jam** ({total_pod_hours/24:.2f} hari)")
    st.write(f"- Total Durasi (POL + POD): **{total_hours:.2f} jam** ({total_days:.2f} hari)")
    st.write(f"- Free Time (Prorata): **{prorata_days:.2f} hari**")
    st.write(f"- Detention / Demurrage Days: **{detention_days:.2f} hari**")
    st.write(f"- Total Biaya Demurrage: **{format_rp(total_cost)}**")

    # Prepare context for PDF
    context = {
        "tug_boat": tug_boat,
        "barge": barge,
        "pol": pol,
        "pod": pod,
        "shipper": shipper,
        "laycan": laycan,
        "prorata_days": prorata_days,
        "rate_demurrage": rate_demurrage,
        "pol_rows": pol_rows,
        "pod_rows": pod_rows,
        "total_pol_hours": total_pol_hours,
        "total_pod_hours": total_pod_hours,
        "total_hours": total_hours,
        "total_days": total_days,
        "detention_days": detention_days,
        "total_cost": total_cost,
    }

    # Generate PDF
    pdf_bytes = build_pdf_bytes(context)
    st.download_button(
        label="📄 Download Voyage Report (PDF)",
        data=pdf_bytes,
        file_name=f"Voyage_Report_{tug_boat or 'vessel'}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
