import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ===============================
# ⚓ PAGE CONFIG
# ===============================
st.set_page_config(page_title="⚓ Voyage Report – Detention/Demurrage", layout="wide")
st.title("⚓ Voyage Report – Barge Detention/Demurrage Calculator")

# ===============================
# 🧭 MODE INPUT
# ===============================
st.markdown("## 📥 Input Data Utama")

col1, col2 = st.columns(2)
with col1:
    tug_boat = st.text_input("Tug Boat Name")
    pol = st.text_input("Port of Loading (POL)")
    shipper = st.text_input("Shipper")
with col2:
    barge = st.text_input("Barge Name")
    pod = st.text_input("Port of Discharge (POD)")
    laycan = st.text_input("Laycan (contoh: 20–22 Oct 2025)")

col3, col4 = st.columns(2)
with col3:
    prorata_days = st.number_input("Prorata (Free Time – Hari)", min_value=0.0, step=0.5)
with col4:
    rate_demurrage = st.number_input("Rate Demurrage (Rp/Hari)", min_value=0.0, step=1000000.0, format="%.0f")

st.markdown("---")

# ===============================
# 📄 VOYAGE REPORT TABLE
# ===============================
st.markdown("## 🧭 Voyage Report")

if "voyage_data" not in st.session_state:
    st.session_state.voyage_data = pd.DataFrame(columns=["Location", "Date", "From", "To", "Status"])

def add_row():
    st.session_state.voyage_data.loc[len(st.session_state.voyage_data)] = ["", datetime.now().date(), "00:00", "00:00", ""]

st.button("➕ Tambah Baris Voyage", on_click=add_row)

edited_df = st.data_editor(
    st.session_state.voyage_data,
    num_rows="dynamic",
    columns={
        "Location": st.column_config.SelectboxColumn("Location", options=["POL", "POD"]),
        "Date": st.column_config.DateColumn("Date"),
        "From": st.column_config.TextColumn("From (HH:MM)"),
        "To": st.column_config.TextColumn("To (HH:MM)"),
        "Status": st.column_config.TextColumn("Status"),
    },
    key="voyage_editor",
)

st.session_state.voyage_data = edited_df

st.markdown("---")

# ===============================
# 🧮 PERHITUNGAN
# ===============================
st.markdown("## 🧮 Perhitungan")

def calculate_duration(df):
    total_hours_pol, total_hours_pod = 0, 0
    for _, row in df.iterrows():
        try:
            t1 = datetime.strptime(row["From"], "%H:%M")
            t2 = datetime.strptime(row["To"], "%H:%M")
            dur = (t2 - t1).total_seconds() / 3600
            if dur < 0:  # kalau jam to < from (lewat tengah malam)
                dur += 24
            if row["Location"] == "POL":
                total_hours_pol += dur
            elif row["Location"] == "POD":
                total_hours_pod += dur
        except:
            continue
    return total_hours_pol, total_hours_pod

if st.button("🚢 Hitung Detention / Demurrage"):
    total_pol, total_pod = calculate_duration(edited_df)
    total_hours = total_pol + total_pod
    total_days = total_hours / 24
    detention_days = max(0, total_days - prorata_days)
    total_cost = detention_days * rate_demurrage

    st.success("✅ Perhitungan selesai!")
    st.markdown(f"**Durasi POL:** {total_pol:.2f} jam ({total_pol/24:.2f} hari)")
    st.markdown(f"**Durasi POD:** {total_pod:.2f} jam ({total_pod/24:.2f} hari)")
    st.markdown(f"**Total Durasi:** {total_days:.2f} hari")
    st.markdown(f"**Free Time (Prorata):** {prorata_days:.2f} hari")
    st.markdown(f"**Detention Days:** {detention_days:.2f} hari")
    st.markdown(f"**💰 Total Biaya (Demurrage): Rp {total_cost:,.0f}**")

    # ===============================
    # 🧾 PDF EXPORT
    # ===============================
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=10, spaceAfter=5, textColor=colors.darkblue))

    elements = []
    elements.append(Paragraph("⚓ VOYAGE REPORT – DETENTION / DEMURRAGE", styles["CenterTitle"]))
    elements.append(Spacer(1, 10))

    # --- Info Kapal ---
    elements.append(Paragraph("<b>Informasi Kapal</b>", styles["SubHeader"]))
    info_table = [
        ["Tug Boat", tug_boat],
        ["Barge", barge],
        ["Port of Loading (POL)", pol],
        ["Port of Discharge (POD)", pod],
        ["Shipper", shipper],
        ["Laycan", laycan],
        ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
        ["Rate Demurrage", f"Rp {rate_demurrage:,.0f} / Hari"],
    ]
    t_info = Table(info_table, colWidths=[180, 320])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10)
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # --- Voyage Table ---
    elements.append(Paragraph("<b>Voyage Activity Report</b>", styles["SubHeader"]))
    voyage_data_list = [["Location", "Date", "From", "To", "Status"]] + [
        [str(r["Location"]), str(r["Date"]), str(r["From"]), str(r["To"]), str(r["Status"])] for _, r in edited_df.iterrows()
    ]
    t_voy = Table(voyage_data_list, colWidths=[60, 80, 60, 60, 220])
    t_voy.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9)
    ]))
    elements.append(t_voy)
    elements.append(Spacer(1, 10))

    # --- Summary ---
    elements.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
    summary = [
        ["Durasi POL", f"{total_pol:.2f} Jam ({total_pol/24:.2f} Hari)"],
        ["Durasi POD", f"{total_pod:.2f} Jam ({total_pod/24:.2f} Hari)"],
        ["Total Hari Pemakaian", f"{total_days:.2f} Hari"],
        ["Free Time (Prorata)", f"{prorata_days:.2f} Hari"],
        ["Detention Days", f"{detention_days:.2f} Hari"],
        ["Total Biaya Demurrage", f"Rp {total_cost:,.0f}"],
    ]
    t_sum = Table(summary, colWidths=[250, 250])
    t_sum.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,5), (-1,5), colors.whitesmoke),
        ('TEXTCOLOR', (0,5), (-1,5), colors.red),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10)
    ]))
    elements.append(t_sum)

    doc.build(elements)
    pdf_data = pdf_buffer.getvalue()

    st.download_button(
        label="📄 Download Voyage Report (PDF)",
        data=pdf_data,
        file_name=f"Voyage_Report_{tug_boat or 'Tugboat'}.pdf",
        mime="application/pdf"
    )
