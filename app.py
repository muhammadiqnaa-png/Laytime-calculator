import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Laytime Calculator", layout="centered")

st.title("⚓ Laytime Calculation Report")

# ==============================
# MODE INPUT
# ==============================
st.subheader("🧭 Mode Input")

col1, col2 = st.columns(2)
with col1:
    tug_name = st.text_input("Tug Boat Name")
with col2:
    barge_name = st.text_input("Barge Name")

col3, col4 = st.columns(2)
with col3:
    pol = st.text_input("Port of Loading (POL)")
with col4:
    pod = st.text_input("Port of Discharge (POD)")

shipper = st.text_input("Shipper Name")

col5, col6 = st.columns(2)
with col5:
    laycan_start = st.date_input("Laycan Start")
with col6:
    laycan_end = st.date_input("Laycan End")

col7, col8 = st.columns(2)
with col7:
    prorata_days = st.number_input("Prorata (days)", value=0.0, step=0.1)
with col8:
    rate_per_day = st.number_input("Rate per Day (USD)", value=0.0, step=100.0)

# ==============================
# VOYAGE REPORT
# ==============================
st.subheader("📋 Voyage Report")

if "voyage_data" not in st.session_state:
    st.session_state.voyage_data = pd.DataFrame(
        columns=["Location", "Date", "Time", "Description"]
    )

# Tambah data baru
with st.expander("➕ Add Voyage Entry"):
    colA, colB, colC, colD = st.columns(4)
    with colA:
        loc = st.selectbox("Location", ["POL", "POD"])
    with colB:
        date_val = st.date_input("Date")
    with colC:
        time_val = st.time_input("Time")
    with colD:
        desc = st.text_input("Description")

    if st.button("Add Entry"):
        new_row = {
            "Location": loc,
            "Date": date_val.strftime("%Y-%m-%d"),
            "Time": time_val.strftime("%H:%M"),
            "Description": desc,
        }
        st.session_state.voyage_data = pd.concat(
            [st.session_state.voyage_data, pd.DataFrame([new_row])],
            ignore_index=True,
        )
        st.success("✅ Entry added successfully!")

# Tampilkan data
st.dataframe(st.session_state.voyage_data, use_container_width=True)

# ==============================
# CALCULATION SECTION
# ==============================
st.subheader("🧮 Calculation")

if st.button("Calculate Laytime"):
    df = st.session_state.voyage_data

    if not df.empty:
        # Pisahkan POL dan POD
        df_pol = df[df["Location"] == "POL"]
        df_pod = df[df["Location"] == "POD"]

        def calc_duration(sub_df):
            if sub_df.empty:
                return 0
            sub_df["datetime"] = pd.to_datetime(sub_df["Date"] + " " + sub_df["Time"])
            start = sub_df["datetime"].min()
            end = sub_df["datetime"].max()
            dur = (end - start).total_seconds() / 3600  # jam
            return dur

        dur_pol = calc_duration(df_pol)
        dur_pod = calc_duration(df_pod)
        total_hours = dur_pol + dur_pod
        total_days = total_hours / 24
        final_days = max(0, total_days - prorata_days)
        total_cost = final_days * rate_per_day

        # Tampilkan hasil
        st.markdown("### 📊 Result Summary")
        st.write(f"**Duration POL:** {dur_pol:.2f} hours ({dur_pol/24:.2f} days)")
        st.write(f"**Duration POD:** {dur_pod:.2f} hours ({dur_pod/24:.2f} days)")
        st.write(f"**Total Duration:** {total_hours:.2f} hours ({total_days:.2f} days)")
        st.write(f"**After Prorata ({prorata_days} days):** {final_days:.2f} days")
        st.write(f"**Total Cost:** ${total_cost:,.2f}")

        # ==============================
        # PDF GENERATION
        # ==============================
        pdf_buffer = BytesIO()
        pdf = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        content = []

        content.append(Paragraph("⚓ Laytime Calculation Report", styles["Title"]))
        content.append(Spacer(1, 12))

        # Header info
        info_data = [
            ["Tug Boat", tug_name],
            ["Barge", barge_name],
            ["Port of Loading (POL)", pol],
            ["Port of Discharge (POD)", pod],
            ["Shipper", shipper],
            ["Laycan", f"{laycan_start} to {laycan_end}"],
            ["Prorata (days)", str(prorata_days)],
            ["Rate per Day (USD)", f"${rate_per_day:,.2f}"],
        ]
        info_table = Table(info_data, colWidths=[180, 350])
        info_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ]))
        content.append(info_table)
        content.append(Spacer(1, 12))

        # Voyage Report Table
        content.append(Paragraph("📋 Voyage Report", styles["Heading2"]))
        table_data = [["Location", "Date", "Time", "Description"]] + df.values.tolist()
        table = Table(table_data, colWidths=[70, 90, 70, 250])
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ]))
        content.append(table)
        content.append(Spacer(1, 12))

        # Calculation summary
        calc_data = [
            ["Duration POL", f"{dur_pol:.2f} hrs / {dur_pol/24:.2f} days"],
            ["Duration POD", f"{dur_pod:.2f} hrs / {dur_pod/24:.2f} days"],
            ["Total Duration", f"{total_hours:.2f} hrs / {total_days:.2f} days"],
            ["After Prorata", f"{final_days:.2f} days"],
            ["Total Cost", f"${total_cost:,.2f}"],
        ]
        calc_table = Table(calc_data, colWidths=[200, 330])
        calc_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        content.append(calc_table)

        pdf.build(content)

        # Nama file otomatis
        date_str = datetime.now().strftime("%Y-%m-%d")
        pdf_name = f"Calculation_Laytime_TB_{tug_name}_{pol}-{pod}_{date_str}.pdf"

        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_buffer.getvalue(),
            file_name=pdf_name,
            mime="application/pdf",
        )
    else:
        st.warning("⚠️ Please add at least one Voyage Report entry first!")
