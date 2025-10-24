import streamlit as st
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- Konfigurasi halaman ---
st.set_page_config(page_title="Detention Calculator — Barge", layout="centered")

st.title("⚓ Detention Calculator — Barge Mode")
st.caption("Hitung detention gabungan untuk POL & POD. Hasil bisa di-download sebagai PDF.")

# --- Fungsi bantu ---
def seconds_to_days(sec):
    return sec / 86400.0  # 1 hari = 86400 detik

def format_rp(x):
    try:
        xi = int(round(x))
        return "Rp {:,}".format(xi).replace(",", ".")
    except:
        return f"Rp {x}"

# --- Form Input ---
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

    pol_start_date = st.date_input("Tanggal Mulai Laytime (Arrival/NOR) — POL", value=datetime.now().date())
    pol_start_time = st.time_input("Jam Mulai — POL", value=datetime.now().time())
    pol_start = datetime.combine(pol_start_date, pol_start_time)

    pol_end_date = st.date_input("Tanggal Selesai Loading — POL", value=datetime.now().date())
    pol_end_time = st.time_input("Jam Selesai — POL", value=datetime.now().time())
    pol_end = datetime.combine(pol_end_date, pol_end_time)

    st.markdown("---")
    st.subheader("Pelabuhan B — POD (isi sesuai POD)")

    pod_start_date = st.date_input("Tanggal Mulai Laytime (Arrival/NOR) — POD", value=datetime.now().date())
    pod_start_time = st.time_input("Jam Mulai — POD", value=datetime.now().time())
    pod_start = datetime.combine(pod_start_date, pod_start_time)

    pod_end_date = st.date_input("Tanggal Selesai Bongkar — POD", value=datetime.now().date())
    pod_end_time = st.time_input("Jam Selesai — POD", value=datetime.now().time())
    pod_end = datetime.combine(pod_end_date, pod_end_time)

    # Tombol submit harus DI DALAM form
    submitted = st.form_submit_button("🚢 Hitung Detention")

# --- Proses perhitungan ---
if submitted:
    # Hitung durasi POL dan POD
    pol_seconds = abs((pol_end - pol_start).total_seconds())
    pod_seconds = abs((pod_end - pod_start).total_seconds())

    pol_days = seconds_to_days(pol_seconds)
    pod_days = seconds_to_days(pod_seconds)
    total_days_used = pol_days + pod_days

    detention_days = max(0.0, total_days_used - prorata_days)
    total_cost = detention_days * rate_per_day

    # Pembulatan
    pol_days_r = round(pol_days, 3)
    pod_days_r = round(pod_days, 3)
    total_days_r = round(total_days_used, 3)
    detention_days_r = round(detention_days, 3)

    # --- Tampilkan hasil ---
    st.markdown("## 🧮 Hasil Perhitungan")
    st.write(f"**Nama Kapal:** {vessel_name or '-'}")
    st.write(f"**Nama Tongkang:** {barge_name or '-'}")
    st.write(f"**POL:** {pol or '-'} | **POD:** {pod or '-'}")

    st.markdown("---")
    st.subheader("Ringkasan Durasi")
    st.write(f"- Durasi di POL: **{pol_days_r} hari** (dari {pol_start} sampai {pol_end})")
    st.write(f"- Durasi di POD: **{pod_days_r} hari** (dari {pod_start} sampai {pod_end})")
    st.write(f"- **Total Hari Terpakai:** {total_days_r} hari")

    st.markdown("---")
    st.subheader("Perhitungan Detention")
    st.write(f"- Free Time (Prorata): **{prorata_days} hari**")
    st.write(f"- Detention Days: **{detention_days_r} hari**")
    st.write(f"- Rate per hari: **{format_rp(rate_per_day)}**")
    st.write(f"### 💰 Total Biaya Detention: **{format_rp(total_cost)}**")

    # --- PDF Generator ---
    def generate_pdf():
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("⚓ Detention Calculator — Barge Mode", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Nama Kapal: {vessel_name or '-'}", styles["Normal"]))
        story.append(Paragraph(f"Nama Tongkang: {barge_name or '-'}", styles["Normal"]))
        story.append(Paragraph(f"POL: {pol or '-'}", styles["Normal"]))
        story.append(Paragraph(f"POD: {pod or '-'}", styles["Normal"]))
        story.append(Spacer(1, 12))

        data = [
            ["Item", "Nilai"],
            ["Durasi di POL (hari)", f"{pol_days_r}"],
            ["Durasi di POD (hari)", f"{pod_days_r}"],
            ["Total Hari Terpakai", f"{total_days_r}"],
            ["Free Time (hari)", f"{prorata_days}"],
            ["Detention Days", f"{detention_days_r}"],
            ["Rate per Hari", f"{format_rp(rate_per_day)}"],
            ["Total Biaya Detention", f"{format_rp(total_cost)}"]
        ]

        table = Table(data, colWidths=[220, 200])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))
        story.append(Paragraph("Note: Perhitungan berdasarkan total durasi POL + POD.", styles["Italic"]))

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    pdf_bytes = generate_pdf()
    st.download_button("📄 Download PDF", data=pdf_bytes, file_name="detention_report.pdf", mime="application/pdf")

    st.success("✅ Perhitungan selesai! PDF siap diunduh.")
else:
    st.info("Isi semua data di atas lalu klik **🚢 Hitung Detention** untuk melihat hasil.")
