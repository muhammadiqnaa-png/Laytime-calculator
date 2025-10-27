import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="⚓ Voyage Demurrage Report", layout="wide")
st.title("⚓ Detention / Demurrage Voyage Report – Barge Mode")

# ========================
# 🧩 Session Initialization
# ========================
if "pol_rows" not in st.session_state:
    st.session_state.pol_rows = []
if "pod_rows" not in st.session_state:
    st.session_state.pod_rows = []

def default_time():
    return time(8, 0)

# ========================
# ⚙️ Mode Input
# ========================
st.header("🧾 Mode Input")

col1, col2 = st.columns(2)
with col1:
    tugboat = st.text_input("Tug Boat")
with col2:
    barge = st.text_input("Barge")

col3, col4 = st.columns(2)
with col3:
    pol = st.text_input("Port of Loading (POL)")
with col4:
    pod = st.text_input("Port of Discharge (POD)")

col5, col6 = st.columns(2)
with col5:
    shipper = st.text_input("Shipper")
with col6:
    laycan = st.text_input("Laycan")

col7, col8 = st.columns(2)
with col7:
    prorata = st.number_input("Free Time (Prorata Days)", min_value=0.0, step=0.5)
with col8:
    rate_per_day = st.number_input("Rate Demurrage (Rp/Day)", min_value=0.0, step=500000.0, format="%.0f")

st.markdown("---")

# ========================
# 🧭 VOYAGE REPORT – POL
# ========================
st.subheader("1️⃣ Port of Loading (POL) – Voyage Events")

def add_pol_row():
    st.session_state.pol_rows.append({
        "Date": date.today(), "From": default_time(), "To": default_time(), "Status": ""
    })

pol_col1, pol_col2 = st.columns([3,1])
with pol_col1:
    st.write("Isi kegiatan di pelabuhan muat (POL).")
with pol_col2:
    st.button("➕ Tambah Baris POL", on_click=add_pol_row)

new_pol = []
for i, row in enumerate(st.session_state.pol_rows):
    cols = st.columns([0.5,2,1,1,3,0.6])
    cols[0].markdown(f"**{i+1}**")
    d = cols[1].date_input("Date", value=row["Date"], key=f"pol_date_{i}_input")
    f = cols[2].time_input("From", value=row["From"], key=f"pol_from_{i}_input", step=60)
    t = cols[3].time_input("To", value=row["To"], key=f"pol_to_{i}_input", step=60)
    s = cols[4].text_input("Status", value=row["Status"], key=f"pol_status_{i}_input")
    remove = cols[5].button("❌", key=f"pol_remove_{i}_btn")
    if not remove:
        new_pol.append({"Date": d, "From": f, "To": t, "Status": s})
st.session_state.pol_rows = new_pol

st.markdown("---")

# ========================
# ⚓ VOYAGE REPORT – POD
# ========================
st.subheader("2️⃣ Port of Discharge (POD) – Voyage Events")

def add_pod_row():
    st.session_state.pod_rows.append({
        "Date": date.today(), "From": default_time(), "To": default_time(), "Status": ""
    })

pod_col1, pod_col2 = st.columns([3,1])
with pod_col1:
    st.write("Isi kegiatan di pelabuhan bongkar (POD).")
with pod_col2:
    st.button("➕ Tambah Baris POD", on_click=add_pod_row)

new_pod = []
for i, row in enumerate(st.session_state.pod_rows):
    cols = st.columns([0.5,2,1,1,3,0.6])
    cols[0].markdown(f"**{i+1}**")
    d = cols[1].date_input("Date", value=row["Date"], key=f"pod_date_{i}_input")
    f = cols[2].time_input("From", value=row["From"], key=f"pod_from_{i}_input", step=60)
    t = cols[3].time_input("To", value=row["To"], key=f"pod_to_{i}_input", step=60)
    s = cols[4].text_input("Status", value=row["Status"], key=f"pod_status_{i}_input")
    remove = cols[5].button("❌", key=f"pod_remove_{i}_btn")
    if not remove:
        new_pod.append({"Date": d, "From": f, "To": t, "Status": s})
st.session_state.pod_rows = new_pod

st.markdown("---")

# ========================
# 🧮 CALCULATION
# ========================
st.subheader("📊 Hasil Perhitungan")

def calc_duration(rows):
    total_hours = 0
    for r in rows:
        start = datetime.combine(r["Date"], r["From"])
        end = datetime.combine(r["Date"], r["To"])
        diff = (end - start).total_seconds() / 3600
        if diff > 0:
            total_hours += diff
    return total_hours

pol_hours = calc_duration(st.session_state.pol_rows)
pod_hours = calc_duration(st.session_state.pod_rows)
total_hours = pol_hours + pod_hours
total_days = total_hours / 24
detention_days = max(0, total_days - prorata)
detention_cost = detention_days * rate_per_day

st.write(f"**Durasi POL:** {pol_hours:.2f} Jam ({pol_hours/24:.2f} Hari)")
st.write(f"**Durasi POD:** {pod_hours:.2f} Jam ({pod_hours/24:.2f} Hari)")
st.write(f"**Total Hari Pemakaian:** {total_days:.2f} Hari")
st.write(f"**Free Time (Prorata):** {prorata:.2f} Hari")
st.write(f"**Detention Days:** {detention_days:.2f} Hari")
st.write(f"**Total Demurrage:** Rp {detention_cost:,.0f}")

st.markdown("---")

# ========================
# 📄 PDF EXPORT
# ========================
if st.button("📄 Download PDF Report"):
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, textColor=colors.darkblue, spaceAfter=5))

    elements = []
    elements.append(Paragraph("⚓ DETENTION / DEMURRAGE REPORT – BARGE", styles["CenterTitle"]))
    elements.append(Spacer(1, 10))

    # Info utama
    elements.append(Paragraph("<b>Informasi Kapal & Voyage</b>", styles["SubHeader"]))
    info_data = [
        ["Tug Boat", tugboat],
        ["Barge", barge],
        ["Port of Loading", pol],
        ["Port of Discharge", pod],
        ["Shipper", shipper],
        ["Laycan", laycan],
        ["Prorata (Free Time)", f"{prorata:.2f} Hari"],
        ["Rate Demurrage", f"Rp {rate_per_day:,.0f} / Hari"],
    ]
    t_info = Table(info_data, colWidths=[180, 320])
    t_info.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # Voyage POL
    elements.append(Paragraph("<b>Voyage Report – POL</b>", styles["SubHeader"]))
    pol_table = [["Date", "From", "To", "Status"]]
    for r in st.session_state.pol_rows:
        pol_table.append([
            r["Date"].strftime("%d %b %Y"),
            r["From"].strftime("%H:%M"),
            r["To"].strftime("%H:%M"),
            r["Status"],
        ])
    t_pol = Table(pol_table, colWidths=[80,60,60,280])
    t_pol.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    elements.append(t_pol)
    elements.append(Spacer(1, 10))

    # Voyage POD
    elements.append(Paragraph("<b>Voyage Report – POD</b>", styles["SubHeader"]))
    pod_table = [["Date", "From", "To", "Status"]]
    for r in st.session_state.pod_rows:
        pod_table.append([
            r["Date"].strftime("%d %b %Y"),
            r["From"].strftime("%H:%M"),
            r["To"].strftime("%H:%M"),
            r["Status"],
        ])
    t_pod = Table(pod_table, colWidths=[80,60,60,280])
    t_pod.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    elements.append(t_pod)
    elements.append(Spacer(1, 10))

    # Summary
    elements.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
    summary = [
        ["Durasi POL", f"{pol_hours:.2f} Jam ({pol_hours/24:.2f} Hari)"],
        ["Durasi POD", f"{pod_hours:.2f} Jam ({pod_hours/24:.2f} Hari)"],
        ["Total Pemakaian", f"{total_hours:.2f} Jam ({total_days:.2f} Hari)"],
        ["Free Time (Prorata)", f"{prorata:.2f} Hari"],
        ["Detention Days", f"{detention_days:.2f} Hari"],
        ["Total Demurrage", f"Rp {detention_cost:,.0f}"],
    ]
    t_sum = Table(summary, colWidths=[220,250])
    t_sum.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,5), (-1,5), colors.whitesmoke),
        ('TEXTCOLOR', (0,5), (-1,5), colors.red)
    ]))
    elements.append(t_sum)

    doc.build(elements)
    st.download_button(
        label="💾 Simpan PDF",
        data=pdf_buffer.getvalue(),
        file_name=f"Voyage_Report_{tugboat or 'Vessel'}.pdf",
        mime="application/pdf"
    )
