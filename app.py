import streamlit as st
from datetime import datetime, timedelta
import math
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="⚓ Detention Calculator – Barge", layout="wide")
st.title("⚓ Detention Calculator – Barge")

st.markdown("### Input Data")

col1, col2 = st.columns(2)
with col1:
    vessel_name = st.text_input("Nama Kapal (TB)")
with col2:
    barge_name = st.text_input("Nama Tongkang")

col3, col4 = st.columns(2)
with col3:
    pol = st.text_input("POL (Port of Loading)")
with col4:
    pod = st.text_input("POD (Port of Discharge)")

col5, col6 = st.columns(2)
with col5:
    prorata_days = st.number_input("Free Time (Hari / Prorata)", min_value=0.0, step=0.5)
with col6:
    rate_per_day = st.number_input("Rate Detention (Rp/Hari)", min_value=0.0, step=1000000.0, format="%.0f")

st.markdown("---")
st.markdown("### 🅰 Pelabuhan A (POL)")

def stable_time_input(key, label):
    if key not in st.session_state:
        st.session_state[key] = datetime.now().time()
    return st.time_input(label, value=st.session_state[key], step=60)

colA1, colA2 = st.columns(2)
with colA1:
    pol_start_date = st.date_input("Tanggal Mulai Laytime (Arrival/NOR – POL)")
with colA2:
    pol_start_time = stable_time_input("pol_start_time", "Jam Mulai – POL")

colA3, colA4 = st.columns(2)
with colA3:
    pol_end_date = st.date_input("Tanggal Selesai Loading (POL)")
with colA4:
    pol_end_time = stable_time_input("pol_end_time", "Jam Selesai – POL")

st.markdown("---")
st.markdown("### 🅱 Pelabuhan B (POD)")

colB1, colB2 = st.columns(2)
with colB1:
    pod_start_date = st.date_input("Tanggal Mulai Laytime (Arrival/NOR – POD)")
with colB2:
    pod_start_time = stable_time_input("pod_start_time", "Jam Mulai – POD")

colB3, colB4 = st.columns(2)
with colB3:
    pod_end_date = st.date_input("Tanggal Selesai Bongkar (POD)")
with colB4:
    pod_end_time = stable_time_input("pod_end_time", "Jam Selesai – POD")

st.markdown("---")

if st.button("🚢 Hitung Detention"):
    # Gabung tanggal & jam jadi datetime penuh
    pol_start = datetime.combine(pol_start_date, pol_start_time)
    pol_end = datetime.combine(pol_end_date, pol_end_time)
    pod_start = datetime.combine(pod_start_date, pod_start_time)
    pod_end = datetime.combine(pod_end_date, pod_end_time)

    # Durasi POL dan POD
    pol_duration = (pol_end - pol_start)
    pod_duration = (pod_end - pod_start)

    total_duration = pol_duration + pod_duration
    total_hours = total_duration.total_seconds() / 3600
    total_days = total_hours / 24

    detention_days = max(0, total_days - prorata_days)
    detention_cost = detention_days * rate_per_day

    st.subheader("📊 Hasil Perhitungan")
    st.write(f"**Total Durasi POL:** {pol_duration.total_seconds()/3600:.2f} jam")
    st.write(f"**Total Durasi POD:** {pod_duration.total_seconds()/3600:.2f} jam")
    st.write(f"**Total Hari Pemakaian:** {total_days:.2f} hari")
    st.write(f"**Free Time (Prorata):** {prorata_days:.2f} hari")
    st.write(f"**Detention Days:** {detention_days:.2f} hari")
    st.write(f"**Total Biaya Detention:** Rp {detention_cost:,.0f}")

    # ===== PDF EXPORT =====
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=10, spaceAfter=5, textColor=colors.darkblue))

    elements = []
    elements.append(Paragraph("⚓ DETENTION REPORT – BARGE", styles["CenterTitle"]))
    elements.append(Spacer(1, 10))

    # Info umum
    elements.append(Paragraph("<b>Informasi Kapal</b>", styles["SubHeader"]))
    data_info = [
        ["Tug Boat (TB)", vessel_name],
        ["Tongkang (Barge)", barge_name],
        ["POL (Port of Loading)", pol],
        ["POD (Port of Discharge)", pod],
        ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
        ["Rate Detention", f"Rp {rate_per_day:,.0f} / Hari"],
    ]
    table_info = Table(data_info, colWidths=[180, 320])
    table_info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_info)
    elements.append(Spacer(1, 10))

    # POL Section
    elements.append(Paragraph("<b>Pelabuhan A (POL)</b>", styles["SubHeader"]))
    data_pol = [
        ["Mulai Laytime (Arrival/NOR – POL)", f"{pol_start.strftime('%d %b %Y %H:%M')}"],
        ["Selesai Loading (POL)", f"{pol_end.strftime('%d %b %Y %H:%M')}"],
        ["Durasi POL", f"{pol_duration.total_seconds()/3600:.2f} Jam ({pol_duration.total_seconds()/(3600*24):.2f} Hari)"],
    ]
    table_pol = Table(data_pol, colWidths=[250, 250])
    table_pol.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_pol)
    elements.append(Spacer(1, 10))

    # POD Section
    elements.append(Paragraph("<b>Pelabuhan B (POD)</b>", styles["SubHeader"]))
    data_pod = [
        ["Mulai Laytime (Arrival/NOR – POD)", f"{pod_start.strftime('%d %b %Y %H:%M')}"],
        ["Selesai Bongkar (POD)", f"{pod_end.strftime('%d %b %Y %H:%M')}"],
        ["Durasi POD", f"{pod_duration.total_seconds()/3600:.2f} Jam ({pod_duration.total_seconds()/(3600*24):.2f} Hari)"],
    ]
    table_pod = Table(data_pod, colWidths=[250, 250])
    table_pod.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_pod)
    elements.append(Spacer(1, 10))

    # Summary Section
    elements.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
    data_summary = [
        ["Total Durasi", f"{total_hours:.2f} Jam ({total_days:.2f} Hari)"],
        ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
        ["Detention Days", f"{detention_days:.2f} Hari"],
        ["Total Biaya Detention", f"Rp {detention_cost:,.0f}"],
    ]
    table_summary = Table(data_summary, colWidths=[250, 250])
    table_summary.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 3), (-1, 3), colors.whitesmoke),
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.red),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table_summary)

    doc.build(elements)
    pdf_data = pdf_buffer.getvalue()

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_data,
        file_name=f"Detention_Report_{vessel_name or 'Vessel'}.pdf",
        mime="application/pdf"
    )
