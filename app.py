import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ==============================
# TITLE
# ==============================
st.set_page_config(page_title="Freight Calculator", layout="wide")
st.title("🚢 Freight Calculator")

# ==============================
# INPUT DATA (SIDEBAR)
# ==============================
st.sidebar.header("⚙️ Input Data Voyage")

# Data Kapal
st.sidebar.subheader("Kapal")
spd = st.sidebar.number_input("Speed (knot)", value=10.0)
dwt = st.sidebar.number_input("DWT (MT)", value=10000.0)
cons = st.sidebar.number_input("Consumption (liter/jam)", value=500.0)

# Data Voyage
st.sidebar.subheader("Voyage")
dist = st.sidebar.number_input("Distance (NM)", value=1000.0)
port_time = st.sidebar.number_input("Port Time (hari)", value=2.0)

# Biaya Mode
st.sidebar.subheader("Biaya Mode")
bbm_price = st.sidebar.number_input("Harga BBM (Rp/liter)", value=10000)
crew_cost = st.sidebar.number_input("Crew Cost (Rp/hari)", value=5000000)
port_cost = st.sidebar.number_input("Port Cost (Rp)", value=10000000)

# Biaya Umum
st.sidebar.subheader("Biaya Umum")
insurance = st.sidebar.number_input("Insurance (%)", value=2.0)
repair = st.sidebar.number_input("Repair & Maintenance (%)", value=3.0)

# Profit
st.sidebar.subheader("Profit % Range")
min_profit = st.sidebar.number_input("Min Profit %", value=5)
max_profit = st.sidebar.number_input("Max Profit %", value=30)
step_profit = st.sidebar.number_input("Step %", value=5)

# POL & POD
pol = st.sidebar.text_input("Port of Loading (POL)", "Tanjung Priok")
pod = st.sidebar.text_input("Port of Discharge (POD)", "Samarinda")

# ==============================
# PERHITUNGAN
# ==============================
sailing_time = dist / spd * 24              # jam
voyage_days = (sailing_time / 24) + port_time
total_consumption = sailing_time * cons
total_bbm = total_consumption * bbm_price
crew_total = crew_cost * voyage_days

biaya_mode = {
    "BBM": total_bbm,
    "Crew": crew_total,
    "Port": port_cost
}

biaya_umum = {
    "Insurance": (insurance / 100) * total_bbm,
    "Repair & Maintenance": (repair / 100) * total_bbm
}

total_cost = sum(biaya_mode.values()) + sum(biaya_umum.values())
cost_per_mt = total_cost / dwt

profit_data = []
for p in range(min_profit, max_profit + 1, step_profit):
    freight_rate = cost_per_mt * (1 + p / 100)
    revenue = freight_rate * dwt
    net_profit = revenue - total_cost
    profit_data.append({"Profit %": p, "Freight Rate": freight_rate, "Net Profit": net_profit})

profit_df = pd.DataFrame(profit_data)

# ==============================
# OUTPUT
# ==============================
st.header("📊 Ringkasan Voyage")

col1, col2, col3, col4 = st.columns(4)
col1.metric("⏱ Sailing Time (jam)", f"{sailing_time:,.2f}")
col2.metric("📆 Voyage Days", f"{voyage_days:,.2f}")
col3.metric("⛽ Consumption (liter)", f"{total_consumption:,.0f}")
col4.metric("💸 Cost per MT", f"Rp {cost_per_mt:,.0f}")

# ------------------------------
# Biaya Mode & Umum
# ------------------------------
with st.expander("💰 Rincian Biaya Mode"):
    biaya_mode_df = pd.DataFrame(biaya_mode.items(), columns=["Komponen","Biaya (Rp)"])
    st.table(biaya_mode_df)

with st.expander("💰 Rincian Biaya Umum"):
    biaya_umum_df = pd.DataFrame(biaya_umum.items(), columns=["Komponen","Biaya (Rp)"])
    st.table(biaya_umum_df)

st.subheader("🧮 Total Cost")
st.success(f"TOTAL COST: Rp {total_cost:,.0f}")

# ------------------------------
# Grafik & Tabel Profit
# ------------------------------
st.subheader("📈 Analisis Profit")

profit_chart = alt.Chart(profit_df).mark_line(point=True).encode(
    x="Profit %",
    y="Net Profit",
    tooltip=["Profit %","Freight Rate","Net Profit"]
).properties(title="Grafik Net Profit")

st.altair_chart(profit_chart, use_container_width=True)
st.dataframe(profit_df, use_container_width=True)

# ==============================
# EXPORT PDF
# ==============================
st.subheader("📥 Export Laporan")

def generate_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Freight Report", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Route: {pol} → {pod}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Ringkasan
    summary_data = [
        ["Sailing Time (jam)", f"{sailing_time:,.2f}"],
        ["Voyage Days", f"{voyage_days:,.2f}"],
        ["Consumption (liter)", f"{total_consumption:,.0f}"],
        ["Cost per MT", f"Rp {cost_per_mt:,.0f}"],
        ["TOTAL COST", f"Rp {total_cost:,.0f}"]
    ]
    summary_table = Table(summary_data, hAlign='LEFT')
    summary_table.setStyle(TableStyle([('BACKGROUND',(0,0),(1,0),colors.lightgrey),
                                       ('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Profit table
    profit_table_data = [profit_df.columns.tolist()] + profit_df.values.tolist()
    profit_table = Table(profit_table_data, hAlign='LEFT')
    profit_table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(profit_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

pdf_buffer = generate_pdf()
st.download_button("📄 Download PDF", data=pdf_buffer,
                   file_name=f"Freight_Report_{pol}_{pod}.pdf",
                   mime="application/pdf")