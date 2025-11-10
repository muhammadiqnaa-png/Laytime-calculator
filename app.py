import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==========================================================
# Fungsi bantu format angka cargo (manual Indonesia format)
# ==========================================================
def format_cargo(value):
    try:
        val = float(value)
        formatted = f"{val:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} MT"
    except:
        return f"{value} MT"

# ==========================================================
# Halaman Utama
# ==========================================================
st.title("🚢 Laytime Calculator App")

# ------------------------
# Voyage Info Section
# ------------------------
st.header("📄 Voyage Information")
col1, col2 = st.columns(2)

with col1:
    tugboat = st.text_input("Tug Boat")
    barge = st.text_input("Barge")
    shipper = st.text_input("Shipper")
    laycan = st.text_input("Laycan")

with col2:
    pol = st.text_input("Port of Loading (POL)")
    pod = st.text_input("Port of Discharge (POD)")
    total_cargo = st.number_input("Total Cargo (MT)", min_value=0.0, format="%.3f")
    free_time = st.text_input("Free Time")
    rate_dem = st.text_input("Rate Demurrage (USD/Day)")

# ------------------------
# Input Status
# ------------------------
st.header("⚓ Status Log (Manual Entry)")

st.markdown("""
Isi manual tanggal, jam, dan statusnya.  
Sistem akan otomatis menghitung durasi antar baris (jam).
""")

data = st.session_state.get("laytime_data", pd.DataFrame(columns=["Date", "Time", "Status"]))

# Form input baris baru
with st.form("add_row"):
    c1, c2, c3 = st.columns(3)
    with c1:
        date = st.date_input("Date")
    with c2:
        time = st.time_input("Time")
    with c3:
        status = st.text_input("Status")

    submitted = st.form_submit_button("➕ Add Row")
    if submitted:
        new_row = pd.DataFrame([{
            "Date": date.strftime("%Y-%m-%d"),
            "Time": time.strftime("%H:%M"),
            "Status": status
        }])
        data = pd.concat([data, new_row], ignore_index=True)
        st.session_state["laytime_data"] = data

# Hapus data
if st.button("🗑️ Clear All Data"):
    data = pd.DataFrame(columns=["Date", "Time", "Status"])
    st.session_state["laytime_data"] = data

# ------------------------
# Hitung Durasi Otomatis
# ------------------------
if not data.empty:
    data["Datetime"] = pd.to_datetime(data["Date"] + " " + data["Time"], format="%Y-%m-%d %H:%M")
    data = data.sort_values(by="Datetime").reset_index(drop=True)
    durations = []
    for i in range(len(data)):
        if i == 0:
            durations.append(0)
        else:
            diff = data.loc[i, "Datetime"] - data.loc[i - 1, "Datetime"]
            durations.append(round(diff.total_seconds() / 3600, 3))  # durasi jam
    data["Duration (Hours)"] = durations
    total_duration = round(sum(durations), 3)

    st.subheader("📊 Laytime Summary")
    st.dataframe(data[["Date", "Time", "Status", "Duration (Hours)"]], use_container_width=True)

    st.markdown(f"**⏱️ Total Duration:** {total_duration:,.3f} Hours")

# ==========================================================
# Export PDF
# ==========================================================
def generate_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    style_title = ParagraphStyle('title', fontSize=14, spaceAfter=10, alignment=1)
    story.append(Paragraph("Laytime Calculation Report", style_title))
    story.append(Spacer(1, 10))

    # Voyage Info Table
    voyage_info = [
        ["Tug Boat", tugboat],
        ["Barge", barge],
        ["Shipper", shipper],
        ["Laycan", laycan],
        ["POL", pol],
        ["POD", pod],
        ["Total Cargo", format_cargo(total_cargo)],
        ["Free Time", free_time],
        ["Rate Demurrage", rate_dem],
    ]

    t = Table(voyage_info, colWidths=[4*cm, 11*cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Table Data
    table_data = [["Date", "Time", "Status", "Duration (Hours)"]]
    for _, row in data.iterrows():
        table_data.append([
            row["Date"],
            row["Time"],
            row["Status"],
            f"{row['Duration (Hours)']:,.3f}"
        ])
    table_data.append(["", "", "Total", f"{total_duration:,.3f}"])

    table = Table(table_data, colWidths=[3*cm, 2.5*cm, 7*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Generated by Laytime Calculator", styles["Normal"]))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================================
# Export Excel
# ==========================================================
def generate_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        info_df = pd.DataFrame({
            "Field": ["Tug Boat", "Barge", "Shipper", "Laycan", "POL", "POD",
                      "Total Cargo", "Free Time", "Rate Demurrage"],
            "Value": [tugboat, barge, shipper, laycan, pol, pod,
                      format_cargo(total_cargo), free_time, rate_dem]
        })
        info_df.to_excel(writer, sheet_name="Laytime Report", index=False, startrow=0)

        data_out = data[["Date", "Time", "Status", "Duration (Hours)"]]
        data_out.to_excel(writer, sheet_name="Laytime Report", startrow=len(info_df)+3, index=False)
    output.seek(0)
    return output

# ==========================================================
# Tombol Download
# ==========================================================
if not data.empty:
    pdf_buffer = generate_pdf()
    excel_buffer = generate_excel()

    colA, colB = st.columns(2)
    with colA:
        st.download_button(
            "📄 Download PDF",
            data=pdf_buffer,
            file_name="Laytime_Report.pdf",
            mime="application/pdf"
        )
    with colB:
        st.download_button(
            "📊 Download Excel",
            data=excel_buffer,
            file_name="Laytime_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
