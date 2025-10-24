import streamlit as st
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import math

st.set_page_config(page_title="Detention Calculator — Barge", layout="centered")

st.title("⚓ Detention Calculator — Barge Mode")
st.caption("Hitung detention gabungan untuk POL & POD. Hasil bisa di-download sebagai PDF.")

# --- Inputs ---
with st.form("input_form"):
    st.subheader("Identitas & Kontrak")
    vessel_name = st.text_input("Nama Kapal", placeholder="MV. Contoh")
    barge_name = st.text_input("Nama Tongkang", placeholder="TB Contoh")
    col1, col2 = st.columns(2)
    with col1:
        pol = st.text_input("POL (Port of Loading)", placeholder="Contoh: Samarinda")
        prorata_days = st.number_input("Prorata / Free time (hari)", min_value=0.0, value=8.0, step=0.5)
    with col2:
        pod = st.text_input("POD (Port of Discharge)", placeholder="Contoh: Gresik")
        rate_per_day = st.number_input("Rate Detention (Rp / hari)", min_value=0.0, value=30000000.0, step=100000.0, format="%.2f")

    st.markdown("---")
    st.subheader("Pelabuhan A — POL (isi sesuai POL)")
    pol_start = st.datetime_input("Mulai Laytime (Arrival / NOR) — POL", value=datetime.now())
    pol_end = st.datetime_input("Selesai Loading — POL", value=datetime.now())

    st.markdown("---")
    st.subheader("Pelabuhan B — POD (isi sesuai POD)")
    pod_start = st.datetime_input("Mulai Laytime (Arrival / NOR) — POD", value=datetime.now())
    pod_end = st.datetime_input("Selesai Bongkar — POD", value=datetime.now())

    submitted = st.form_submit_button("Hitung Detention")

# --- Calculation helpers ---
def seconds_to_days_hours_str(sec):
    days = sec / 86400.0
    return days

def format_rp(x):
    try:
        xi = int(round(x))
        return "Rp {:,}".format(xi).replace(",", ".")
    except:
        return f"Rp {x}"

if submitted:
    # Validate datetimes: if end < start, show warning but still compute absolute durations
    pol_delta = (pol_end - pol_start).total_seconds()
    pod_delta = (pod_end - pod_start).total_seconds()

    if pol_delta < 0:
        st.warning("Perhatian: 'Selesai Loading — POL' lebih awal dari 'Mulai Laytime — POL'. Menggunakan nilai absolut durasi.")
        pol_delta = abs(pol_delta)
    if pod_delta < 0:
        st.warning("Perhatian: 'Selesai Bongkar — POD' lebih awal dari 'Mulai Laytime — POD'. Menggunakan nilai absolut durasi.")
        pod_delta = abs(pod_delta)

    # Convert to days (float)
    pol_days = seconds_to_days_hours_str(pol_delta)
    pod_days = seconds_to_days_hours_str(pod_delta)
    total_days_used = pol_days + pod_days

    # Detention calculation
    detention_days = max(0.0, total_days_used - prorata_days)
    total_cost = detention_days * rate_per_day

    # round values sensibly
    pol_days_r = round(pol_days, 3)
    pod_days_r = round(pod_days, 3)
    total_days_r = round(total_days_used, 3)
    detention_days_r = round(detention_days, 3)
    total_cost_r = round(total_cost, 0)

    # --- Output display ---
    st.markdown("### Hasil Perhitungan")
    st.write(f"**Nama Kapal:** {vessel_name or '-'}  \n**Nama Tongkang:** {barge_name or '-'}")
    st.write(f"**POL:** {pol or '-'}  \n**POD:** {pod or '-'}")
    st.markdown("---")

    st.subheader("Ringkasan Durasi")
    st.write(f"- Durasi di POL: **{pol_days_r} hari**  (dari {pol_start} sampai {pol_end})")
    st.write(f"- Durasi di POD: **{pod_days_r} hari**  (dari {pod_start} sampai {pod_end})")
    st.write(f"- **Total Hari Terpakai (POL + POD): {total_days_r} hari**")

    st.markdown("---")
    st.subheader("Perhitungan Detention")
    st.write(f"- Free Time (Prorata): **{prorata_days} hari**")
    st.write(f"- Detention (hari) = max(0, Total Hari - Prorata) = **{detention_days_r} hari**")
    st.write(f"- Rate Detention: **{format_rp(rate_per_day)} / hari**")
    st.write(f"### Total Biaya Detention: **{format_rp(total_cost_r)}**")

    # Breakdown table
    st.markdown("---")
    st.subheader("Breakdown")
    breakdown = {
        "Item": ["POL Duration (hari)", "POD Duration (hari)", "Total Days", "Prorata (hari)", "Detention Days", "Rate / hari", "Total Cost"],
        "Value": [f"{pol_days_r}", f"{pod_days_r}", f"{total_days_r}", f"{prorata_days}", f"{detention_days_r}", f"{format_rp(rate_per_day)}", f"{format_rp(total_cost_r)}"]
    }
    st.table(breakdown)

    # --- Create PDF ---
    def create_pdf_bytes():
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Detention Calculator — Barge Mode", styles["Title"]))
        story.append(Paragraph("", styles["Normal"]))
        story.append(Paragraph(f"Nama Kapal: {vessel_name or '-'}", styles["Normal"]))
        story.append(Paragraph(f"Nama Tongkang: {barge_name or '-'}", styles["Normal"]))
        story.append(Paragraph(f"POL: {pol or '-'}", styles["Normal"]))
        story.append(Paragraph(f"POD: {pod or '-'}", styles["Normal"]))
        story.append(Spacer(1, 10))

        data = [
            ["Item", "Keterangan / Value"],
            ["Durasi di POL (hari)", f"{pol_days_r}"],
            ["Durasi di POD (hari)", f"{pod_days_r}"],
            ["Total Hari Terpakai", f"{total_days_r}"],
            ["Prorata (Free time) hari", f"{prorata_days}"],
            ["Detention Days", f"{detention_days_r}"],
            ["Rate per hari", f"{format_rp(rate_per_day)}"],
            ["Total Biaya Detention", f"{format_rp(total_cost_r)}"]
        ]

        tbl = Table(data, hAlign="LEFT", colWidths=[200, 260])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eeeeee")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 12))
        story.append(Paragraph("Disclaimer: Perhitungan menggunakan asumsi total durasi = durasi POL + durasi POD. Sesuaikan jika aturan kontrak berbeda.", styles["Italic"]))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    pdf_bytes = create_pdf_bytes()
    st.download_button("📄 Download Hasil (PDF)", data=pdf_bytes, file_name="detention_report.pdf", mime="application/pdf")

    st.success("Selesai — perhitungan berhasil dibuat. Cek tampilan dan PDF-nya ya bro.")
    st.caption("Catatan: jika aturan kontrak beda (mis. hitung continuous dari arrival POL sampai selesai POD), beri tau aku dan aku ubah logikanya.")

else:
    st.info("Isi form di atas lalu klik *Hitung Detention* untuk melihat hasil dan mendownload PDF.")
