import streamlit as st
from datetime import datetime, timedelta
import math
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="⚓ Detention Calculator – Barge Mode", layout="wide")
st.title("⚓ Detention Calculator – Barge Mode")

st.markdown("### Input Data")

col1, col2 = st.columns(2)
with col1:
    vessel_name = st.text_input("Nama Kapal")
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

# ===== FIX: SIMPAN JAM DI SESSION STATE =====
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

    total_duration = (pol_end - pol_start) + (pod_end - pod_start)
    total_hours = total_duration.total_seconds() / 3600
    total_days = total_hours / 24

    detention_days = max(0, total_days - prorata_days)
    detention_cost = detention_days * rate_per_day

    st.subheader("📊 Hasil Perhitungan")
    st.write(f"**Total Hari Pemakaian:** {total_days:.2f} hari")
    st.write(f"**Free Time (Prorata):** {prorata_days:.2f} hari")
    st.write(f"**Detention Days:** {detention_days:.2f} hari")
    st.write(f"**Total Biaya Detention:** Rp {detention_cost:,.0f}")

    # ===== PDF EXPORT =====
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("⚓ Detention Report – Barge Mode", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [
        ["Nama Kapal", vessel_name],
        ["Nama Tongkang", barge_name],
        ["POL", pol],
        ["POD", pod],
        ["Free Time (Hari)", f"{prorata_days:.2f}"],
        ["Rate Detention (Rp/Hari)", f"Rp {rate_per_day:,.0f}"],
        ["Total Hari Pemakaian", f"{total_days:.2f}"],
        ["Detention Days", f"{detention_days:.2f}"],
        ["Total Biaya Detention", f"Rp {detention_cost:,.0f}"],
    ]

    table = Table(data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)
    pdf_data = pdf_buffer.getvalue()

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_data,
        file_name="Detention_Report.pdf",
        mime="application/pdf"
    )
