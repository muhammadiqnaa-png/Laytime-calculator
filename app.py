import streamlit as st
from datetime import datetime, date, time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Detention Calculator — Barge", layout="centered")

st.title("⚓ Detention Calculator ")
st.caption("Hitung detention gabungan POL & POD berdasarkan tanggal dan jam. Hasil bisa diunduh sebagai PDF.")

def seconds_to_days(sec): return sec / 86400.0
def format_rp(x):
    try:
        xi = int(round(x))
        return "Rp {:,}".format(xi).replace(",", ".")
    except:
        return f"Rp {x}"

with st.form("input_form"):
    st.subheader("Identitas & Kontrak")
    vessel_name = st.text_input("Nama Kapal")
    barge_name = st.text_input("Nama Tongkang")

    col1, col2 = st.columns(2)
    with col1:
        pol = st.text_input("POL (Port of Loading)")
        prorata_days = st.number_input("Free Time (hari)", min_value=0.0, value=8.0, step=0.5)
    with col2:
        pod = st.text_input("POD (Port of Discharge)")
        rate_per_day = st.number_input("Rate Detention (Rp / hari)", min_value=0.0, value=30000000.0, step=100000.0, format="%.2f")

    st.markdown("---")
    st.subheader("Pelabuhan A — POL")

    colA1, colA2 = st.columns([2, 1])
    with colA1:
        pol_start_date = st.date_input("Tanggal Mulai Laytime (Arrival / NOR) — POL", value=date.today())
    with colA2:
        pol_start_time = st.time_input("Jam Mulai — POL", value=datetime.now().time())

    colA3, colA4 = st.columns([2, 1])
    with colA3:
        pol_end_date = st.date_input("Tanggal Selesai Loading — POL", value=date.today())
    with colA4:
        pol_end_time = st.time_input("Jam Selesai — POL", value=datetime.now().time())

    st.markdown("---")
    st.subheader("Pelabuhan B — POD")

    colB1, colB2 = st.columns([2, 1])
    with colB1:
        pod_start_date = st.date_input("Tanggal Mulai Laytime (Arrival / NOR) — POD", value=date.today())
    with colB2:
        pod_start_time = st.time_input("Jam Mulai — POD", value=datetime.now().time())

    colB3, colB4 = st.columns([2, 1])
    with colB3:
        pod_end_date = st.date_input("Tanggal Selesai Bongkar — POD", value=date.today())
    with colB4:
        pod_end_time = st.time_input("Jam Selesai — POD", value=datetime.now().time())

    submitted = st.form_submit_button("🚢 Hitung Detention")

if submitted:
    # Gabungkan tanggal & jam
    pol_start = datetime.combine(pol_start_date, pol_start_time)
    pol_end = datetime.combine(pol_end_date, pol_end_time)
    pod_start = datetime.combine(pod_start_date, pod_start_time)
    pod_end = datetime.combine(pod_end_date, pod_end_time)

    # Hitung hari
    pol_days = seconds_to_days(abs((pol_end - pol_start).total_seconds()))
    pod_days = seconds_to_days(abs((pod_end - pod_start).total_seconds()))
    total_days_used = pol_days + pod_days
    detention_days = max(0.0, total_days_used - prorata_days)
    total_cost = detention_days * rate_per_day

    st.markdown("## 🧮 Hasil Perhitungan")
    st.write(f"**Total Hari Terpakai:** {round(total_days_used, 3)} hari")
    st.write(f"**Free Time (Prorata):** {prorata_days} hari")
    st.write(f"**Detention Days:** {round(detention_days, 3)} hari")
    st.write(f"**Total Biaya Detention:** {format_rp(total_cost)}")

    def generate_pdf():
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Detention Report — Barge Mode", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Nama Kapal: {vessel_name}", styles["Normal"]))
        story.append(Paragraph(f"Nama Tongkang: {barge_name}", styles["Normal"]))
        story.append(Paragraph(f"POL: {pol} | POD: {pod}", styles["Normal"]))
        story.append(Spacer(1, 12))

        data = [
            ["Item", "Nilai"],
            ["Durasi POL (hari)", f"{round(pol_days,3)}"],
            ["Durasi POD (hari)", f"{round(pod_days,3)}"],
            ["Total Hari", f"{round(total_days_used,3)}"],
            ["Free Time", f"{prorata_days}"],
            ["Detention Days", f"{round(detention_days,3)}"],
            ["Rate / Hari", f"{format_rp(rate_per_day)}"],
            ["Total Cost", f"{format_rp(total_cost)}"],
        ]
        table = Table(data, colWidths=[220, 200])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    pdf_bytes = generate_pdf()
    st.download_button("📄 Download PDF", data=pdf_bytes, file_name="detention_report.pdf", mime="application/pdf")
