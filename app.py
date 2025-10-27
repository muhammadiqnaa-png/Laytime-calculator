import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="⚓ Detention Calculator – Barge", layout="wide")
st.title("⚓ Detention Calculator – Barge Mode")

# =====================================================
# INPUT DATA DASAR
# =====================================================
st.markdown("### Input Data Kapal")

col1, col2 = st.columns(2)
with col1:
    vessel_name = st.text_input("Tug Boat (Vessel Name)")
with col2:
    barge_name = st.text_input("Barge Name")

col3, col4 = st.columns(2)
with col3:
    pol = st.text_input("POL (Port of Loading)")
with col4:
    pod = st.text_input("POD (Port of Discharge)")

col5, col6 = st.columns(2)
with col5:
    prorata_days = st.number_input("Free Time (Prorata / Hari)", min_value=0.0, step=0.5)
with col6:
    rate_per_day = st.number_input("Rate Detention (Rp / Hari)", min_value=0.0, step=1000000.0, format="%.0f")

st.markdown("---")

# =====================================================
# PORT OF LOADING SECTION (POL)
# =====================================================
st.subheader("1️⃣ Port of Loading (POL)")
st.caption(f"Pelabuhan: **{pol or 'Belum diisi'}**")

if "pol_table" not in st.session_state:
    st.session_state["pol_table"] = pd.DataFrame(
        [{"Tanggal": date.today(), "Jam": time(8, 0), "Keterangan": "Arrival / NOR"}]
    )

pol_table = st.data_editor(
    st.session_state["pol_table"],
    num_rows="dynamic",
    use_container_width=True,
    key="pol_editor",
)
st.session_state["pol_table"] = pol_table

# =====================================================
# PORT OF DISCHARGE SECTION (POD)
# =====================================================
st.subheader("2️⃣ Port of Discharge (POD)")
st.caption(f"Pelabuhan: **{pod or 'Belum diisi'}**")

if "pod_table" not in st.session_state:
    st.session_state["pod_table"] = pd.DataFrame(
        [{"Tanggal": date.today(), "Jam": time(8, 0), "Keterangan": "Arrival / NOR"}]
    )

pod_table = st.data_editor(
    st.session_state["pod_table"],
    num_rows="dynamic",
    use_container_width=True,
    key="pod_editor",
)
st.session_state["pod_table"] = pod_table

st.markdown("---")

# =====================================================
# PERHITUNGAN
# =====================================================
if st.button("🚢 Hitung Detention", use_container_width=True):
    try:
        # --- POL Durasi ---
        pol_table_sorted = pol_table.sort_values(by=["Tanggal", "Jam"])
        pol_start = datetime.combine(pol_table_sorted.iloc[0]["Tanggal"], pol_table_sorted.iloc[0]["Jam"])
        pol_end = datetime.combine(pol_table_sorted.iloc[-1]["Tanggal"], pol_table_sorted.iloc[-1]["Jam"])
        pol_duration = (pol_end - pol_start).total_seconds() / 3600  # jam

        # --- POD Durasi ---
        pod_table_sorted = pod_table.sort_values(by=["Tanggal", "Jam"])
        pod_start = datetime.combine(pod_table_sorted.iloc[0]["Tanggal"], pod_table_sorted.iloc[0]["Jam"])
        pod_end = datetime.combine(pod_table_sorted.iloc[-1]["Tanggal"], pod_table_sorted.iloc[-1]["Jam"])
        pod_duration = (pod_end - pod_start).total_seconds() / 3600  # jam

        # --- Total Durasi ---
        total_hours = pol_duration + pod_duration
        total_days = total_hours / 24
        detention_days = max(0, total_days - prorata_days)
        detention_cost = detention_days * rate_per_day

        # =====================================================
        # HASIL TAMPILAN
        # =====================================================
        st.markdown("### 📊 Hasil Perhitungan")
        st.write(f"**Durasi POL:** {pol_duration:.2f} Jam ({pol_duration/24:.2f} Hari)")
        st.write(f"**Durasi POD:** {pod_duration:.2f} Jam ({pod_duration/24:.2f} Hari)")
        st.write(f"**Total Hari Pemakaian:** {total_days:.2f} Hari")
        st.write(f"**Free Time (Prorata):** {prorata_days:.2f} Hari")
        st.write(f"**Detention Days:** {detention_days:.2f} Hari")
        st.write(f"**Total Biaya Detention:** Rp {detention_cost:,.0f}")

        # =====================================================
        # PDF GENERATOR
        # =====================================================
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
        styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=10, spaceAfter=5, textColor=colors.darkblue))

        elements = []
        elements.append(Paragraph("⚓ DETENTION REPORT – BARGE", styles["CenterTitle"]))
        elements.append(Spacer(1, 10))

        # --- Informasi Umum ---
        info_data = [
            ["Tug Boat (TB)", vessel_name],
            ["Tongkang (Barge)", barge_name],
            ["POL (Port of Loading)", pol],
            ["POD (Port of Discharge)", pod],
            ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
            ["Rate Detention", f"Rp {rate_per_day:,.0f} / Hari"],
        ]
        info_table = Table(info_data, colWidths=[180, 320])
        info_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(Paragraph("<b>Informasi Kapal</b>", styles["SubHeader"]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        # --- POL Table ---
        elements.append(Paragraph("<b>Port of Loading (POL)</b>", styles["SubHeader"]))
        pol_data_pdf = [["Tanggal", "Jam", "Keterangan"]] + [
            [row["Tanggal"].strftime("%d %b %Y"), row["Jam"].strftime("%H:%M"), row["Keterangan"]] for _, row in pol_table_sorted.iterrows()
        ]
        table_pol = Table(pol_data_pdf, colWidths=[120, 80, 280])
        table_pol.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table_pol)
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"Durasi POL: {pol_duration:.2f} Jam ({pol_duration/24:.2f} Hari)", styles["Normal"]))
        elements.append(Spacer(1, 10))

        # --- POD Table ---
        elements.append(Paragraph("<b>Port of Discharge (POD)</b>", styles["SubHeader"]))
        pod_data_pdf = [["Tanggal", "Jam", "Keterangan"]] + [
            [row["Tanggal"].strftime("%d %b %Y"), row["Jam"].strftime("%H:%M"), row["Keterangan"]] for _, row in pod_table_sorted.iterrows()
        ]
        table_pod = Table(pod_data_pdf, colWidths=[120, 80, 280])
        table_pod.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table_pod)
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"Durasi POD: {pod_duration:.2f} Jam ({pod_duration/24:.2f} Hari)", styles["Normal"]))
        elements.append(Spacer(1, 10))

        # --- Summary Table ---
        summary_data = [
            ["Total Durasi", f"{total_hours:.2f} Jam ({total_days:.2f} Hari)"],
            ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
            ["Detention Days", f"{detention_days:.2f} Hari"],
            ["Total Biaya Detention", f"Rp {detention_cost:,.0f}"],
        ]
        summary_table = Table(summary_data, colWidths=[250, 250])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 3), (-1, 3), colors.whitesmoke),
            ('TEXTCOLOR', (0, 3), (-1, 3), colors.red),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
        elements.append(summary_table)

        doc.build(elements)
        pdf_data = pdf_buffer.getvalue()

        st.download_button(
            "📄 Download PDF Report",
            data=pdf_data,
            file_name=f"Detention_Report_{vessel_name or 'Barge'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
