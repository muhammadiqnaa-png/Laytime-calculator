import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

DB_PATH = "data.db"

# ==============================
# Database Setup
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS kapal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            speed_isi REAL,
            speed_kosong REAL,
            consumption_isi REAL,
            consumption_kosong REAL,
            consumption_port REAL,
            daily_cost REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# Helper functions
# ==============================
def get_kapal_list():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM kapal", conn)
    conn.close()
    return df

def add_kapal(nama, speed_isi, speed_kosong, consumption_isi, consumption_kosong, consumption_port, daily_cost):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO kapal (nama, speed_isi, speed_kosong, consumption_isi, consumption_kosong, consumption_port, daily_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nama, speed_isi, speed_kosong, consumption_isi, consumption_kosong, consumption_port, daily_cost))
    conn.commit()
    conn.close()

def delete_kapal(nama):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM kapal WHERE nama=?", (nama,))
    conn.commit()
    conn.close()

# ==============================
# Sidebar Layout
# ==============================
st.sidebar.title("⚙️ Pengaturan Perhitungan")

with st.sidebar.expander("📦 Mode & Pilihan Kapal"):
    mode = st.radio("Pilih Mode Perhitungan", ["Owner", "Charter Hire"])
    kapal_list = get_kapal_list()
    kapal_nama = st.selectbox("Pilih Kapal", kapal_list["nama"] if not kapal_list.empty else [])

with st.sidebar.expander("⚓ Data Kapal"):
    nama_kapal = st.text_input("Nama Kapal")
    speed_isi = st.number_input("Speed Isi (Knot)", 0.0)
    speed_kosong = st.number_input("Speed Kosong (Knot)", 0.0)
    cons_isi = st.number_input("Consumption Isi (MT/day)", 0.0)
    cons_kosong = st.number_input("Consumption Kosong (MT/day)", 0.0)
    cons_port = st.number_input("Consumption Port (MT/day)", 0.0)
    daily_cost = st.number_input("Daily Cost (Rp)", 0.0)

    if st.button("💾 Simpan Kapal"):
        add_kapal(nama_kapal, speed_isi, speed_kosong, cons_isi, cons_kosong, cons_port, daily_cost)
        st.success("Data kapal berhasil disimpan!")

    if not kapal_list.empty:
        hapus_kapal = st.selectbox("Hapus Kapal", kapal_list["nama"])
        if st.button("🗑️ Hapus Kapal"):
            delete_kapal(hapus_kapal)
            st.warning(f"Kapal {hapus_kapal} telah dihapus.")

with st.sidebar.expander("⛽ Parameter Voyage"):
    pol = st.text_input("POL (Port of Loading)")
    pod = st.text_input("POD (Port of Discharge)")
    total_cargo = st.number_input("Total Cargo (MT)", 0.0)
    jarak_laden = st.number_input("Jarak Laden (Nm)", 0.0)
    jarak_ballast = st.number_input("Jarak Ballast (Nm)", 0.0)
    harga_bunker = st.number_input("Harga Bunker (Rp/MT)", 0.0)
    port_days = st.number_input("Port Days", 0.0)

with st.sidebar.expander("💰 Biaya Mode"):
    biaya_agency = st.number_input("Biaya Agency (Rp)", 0.0)
    biaya_pilot = st.number_input("Biaya Pilotage (Rp)", 0.0)
    biaya_tugboat = st.number_input("Biaya Tugboat (Rp)", 0.0)
    biaya_port = st.number_input("Biaya Port Charges (Rp)", 0.0)
    biaya_lain = st.number_input("Biaya Lainnya (Rp)", 0.0)

# ==============================
# Perhitungan
# ==============================
st.title("🚢 Freight Calculation System")

kapal_data = kapal_list[kapal_list["nama"] == kapal_nama].iloc[0] if not kapal_list.empty and kapal_nama else None

if kapal_data is not None:
    speed_isi = kapal_data["speed_isi"]
    speed_kosong = kapal_data["speed_kosong"]
    cons_isi = kapal_data["consumption_isi"]
    cons_kosong = kapal_data["consumption_kosong"]
    cons_port = kapal_data["consumption_port"]
    daily_cost = kapal_data["daily_cost"]

# Cegah pembagian nol
sailing_time = (
    (jarak_laden / speed_isi if speed_isi else 0)
    + (jarak_ballast / speed_kosong if speed_kosong else 0)
)
voyage_days = sailing_time + port_days
total_consumption = (
    (sailing_time * ((cons_isi + cons_kosong) / 2)) + (port_days * cons_port)
)
bunker_cost = total_consumption * harga_bunker

# Total biaya mode
total_biaya_mode = (
    biaya_agency + biaya_pilot + biaya_tugboat + biaya_port + biaya_lain
)
total_voyage_cost = bunker_cost + (voyage_days * daily_cost) + total_biaya_mode

freight_per_mt = total_voyage_cost / total_cargo if total_cargo else 0

# ==============================
# Tampilan hasil
# ==============================
st.subheader("📊 Hasil Perhitungan Voyage")

col1, col2 = st.columns(2)
with col1:
    st.metric("Sailing Time (Hari)", round(sailing_time, 2))
    st.metric("Voyage Days", round(voyage_days, 2))
    st.metric("Total Consumption (MT)", round(total_consumption, 2))
with col2:
    st.metric("Total Voyage Cost (Rp)", f"{total_voyage_cost:,.0f}")
    st.metric("Cost per MT (Rp)", f"{freight_per_mt:,.0f}")

# ==============================
# Profit Scenario Table
# ==============================
st.subheader("💹 Profit Scenario")
profit_data = []
for p in range(0, 55, 5):
    profit_value = freight_per_mt * (1 + p / 100)
    profit_data.append([f"{p}%", f"{profit_value:,.0f}"])
df_profit = pd.DataFrame(profit_data, columns=["Profit (%)", "Freight (Rp/MT)"])
st.table(df_profit)

# ==============================
# Export ke PDF
# ==============================
st.subheader("📄 Download Laporan PDF")

def generate_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT", styles["Title"]))
    elements.append(Spacer(1, 10))

    data_header = [
        ["POL", pol],
        ["POD", pod],
        ["Total Cargo (MT)", total_cargo],
        ["Jarak Laden (Nm)", jarak_laden],
        ["Jarak Ballast (Nm)", jarak_ballast],
        ["Harga Bunker (Rp/MT)", f"{harga_bunker:,.0f}"],
    ]
    table1 = Table(data_header, hAlign="LEFT")
    table1.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    elements.append(table1)
    elements.append(Spacer(1, 10))

    data_result = [
        ["Sailing Time (Hari)", round(sailing_time, 2)],
        ["Voyage Days", round(voyage_days, 2)],
        ["Total Consumption (MT)", round(total_consumption, 2)],
        ["Total Voyage Cost (Rp)", f"{total_voyage_cost:,.0f}"],
        ["Cost per MT (Rp)", f"{freight_per_mt:,.0f}"],
    ]
    table2 = Table(data_result, hAlign="LEFT")
    table2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    elements.append(table2)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Profit Scenario", styles["Heading2"]))
    profit_table = [["Profit (%)", "Freight (Rp/MT)"]] + profit_data
    t = Table(profit_table)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("📥 Download PDF"):
    pdf = generate_pdf()
    st.download_button("Klik untuk Download", data=pdf, file_name="freight_report.pdf", mime="application/pdf")
