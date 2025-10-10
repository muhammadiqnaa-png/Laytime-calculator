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
    required_cols = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "nama": "TEXT UNIQUE",
        "total_cargo": "REAL",
        "consumption": "REAL",
        "angsuran": "REAL",
        "crew_cost": "REAL",
        "asuransi": "REAL",
        "docking": "REAL",
        "perawatan": "REAL",
        "sertifikat": "REAL",
        "depresiasi": "REAL",
        "charter_hire": "REAL"
    }
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS kapal (
            {", ".join([f"{col} {dtype}" for col, dtype in required_cols.items()])}
        )
    """)
    conn.commit()
    conn.close()

def get_all_kapal():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM kapal", conn)
    conn.close()
    return df

def get_kapal_by_name(nama):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM kapal WHERE nama=?", (nama,))
    row = c.fetchone()
    conn.close()
    return row

# ==============================
# App Setup
# ==============================
st.set_page_config(page_title="Freight Calculator", layout="wide")
init_db()

# ==============================
# Auth
# ==============================
USER_CREDENTIALS = {"admin": "12345", "user1": "abcde"}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔒 Login Aplikasi Freight Calculator")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Username / password salah")
    st.stop()

# ==============================
# Sidebar
# ==============================
st.sidebar.title("⚙️ Pengaturan Perhitungan")
st.sidebar.success(f"👤 Login sebagai: {st.session_state.username}")

with st.sidebar.expander("🚀 Mode Perhitungan"):
    mode = st.radio("Pilih Mode Biaya:", ["Owner", "Charter"])

with st.sidebar.expander("🛳️ Data Kapal"):
    df_kapal = get_all_kapal()
    kapal_list = ["-- Kapal Baru --"] + df_kapal["nama"].tolist()
    pilihan_kapal = st.selectbox("Pilih Kapal", kapal_list)

kapal_data = None
if pilihan_kapal != "-- Kapal Baru --":
    row = get_kapal_by_name(pilihan_kapal)
    if row:
        _, nama, total_cargo_db, consumption_db, angsuran_db, crew_cost_db, asuransi_db, docking_db, perawatan_db, sertifikat_db, depresiasi_db, charter_hire_db = row + (None,) * (12 - len(row))
        kapal_data = dict(
            nama=nama,
            total_cargo=total_cargo_db or 0,
            consumption=consumption_db or 0,
            angsuran=angsuran_db or 0,
            crew_cost=crew_cost_db or 0,
            asuransi=asuransi_db or 0,
            docking=docking_db or 0,
            perawatan=perawatan_db or 0,
            sertifikat=sertifikat_db or 0,
            depresiasi=depresiasi_db or 0,
            charter_hire=charter_hire_db or 0
        )

with st.sidebar.expander("⚓ Parameter Kapal"):
    consumption = st.number_input("Consumption (liter/jam)", value=float(kapal_data["consumption"]) if kapal_data else 0.0)
    if mode == "Owner":
        angsuran = st.number_input("Angsuran (Rp/bulan)", value=float(kapal_data["angsuran"]) if kapal_data else 0.0)
        crew_cost = st.number_input("Crew Cost (Rp/bulan)", value=float(kapal_data["crew_cost"]) if kapal_data else 0.0)
        asuransi = st.number_input("Asuransi (Rp/bulan)", value=float(kapal_data["asuransi"]) if kapal_data else 0.0)
        docking = st.number_input("Docking (Rp/bulan)", value=float(kapal_data["docking"]) if kapal_data else 0.0)
        perawatan = st.number_input("Perawatan (Rp/bulan)", value=float(kapal_data["perawatan"]) if kapal_data else 0.0)
        sertifikat = st.number_input("Sertifikat (Rp/bulan)", value=float(kapal_data["sertifikat"]) if kapal_data else 0.0)
        depresiasi = st.number_input("Depresiasi (Rp/Beli)", value=float(kapal_data["depresiasi"]) if kapal_data else 0.0)
    else:
        charter_hire = st.number_input("Charter Hire (Rp/bulan)", value=float(kapal_data["charter_hire"]) if kapal_data else 0.0)

with st.sidebar.expander("🧭 Parameter Voyage"):
    speed_kosong = st.number_input("Speed Kosong (knot)", value=0.0)
    speed_isi = st.number_input("Speed Isi (knot)", value=0.0)
    harga_bunker = st.number_input("Harga Bunker (Rp/liter)", value=0.0)
    harga_air_tawar = st.number_input("Harga Air Tawar (Rp/Ton)", value=0.0)
    port_cost = st.number_input("Port Cost/call (Rp)", value=0.0)
    asist_tug = st.number_input("Asist Tug (Rp)", value=0.0)
    premi_nm = st.number_input("Premi (Rp/NM)", value=0.0)
    other_cost = st.number_input("Other Cost (Rp)", value=0.0)
    port_stay = st.number_input("Port Stay (hari)", value=0.0)

# ==============================
# Input Voyage
# ==============================
st.title("🚢 Freight Calculator Tongkang")
pol = st.text_input("Port of Loading (POL)")
pod = st.text_input("Port of Discharge (POD)")
total_cargo = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data else 0.0)
jarak_laden = st.number_input("Jarak Laden (NM)", value=0.0)
jarak_ballast = st.number_input("Jarak Ballast (NM)", value=0.0)

# ==============================
# Perhitungan
# ==============================
sailing_time = (jarak_laden / speed_isi + jarak_ballast / speed_kosong) if speed_isi > 0 and speed_kosong > 0 else 0
voyage_days = (sailing_time / 24) + port_stay
total_consumption = (sailing_time * consumption) + (port_stay * consumption)

biaya_umum = {
    "Bunker BBM": total_consumption * harga_bunker,
    "Air Tawar": (voyage_days * 2) * harga_air_tawar,
    "Port Cost": port_cost * 2,
    "Premi": premi_nm * (jarak_laden + jarak_ballast),
    "Asist": asist_tug
}

if mode == "Owner":
    biaya_mode = {
        "Angsuran": (angsuran / 30) * voyage_days,
        "Crew Cost": (crew_cost / 30) * voyage_days,
        "Asuransi": (asuransi / 30) * voyage_days,
        "Docking": (docking / 30) * voyage_days,
        "Perawatan": (perawatan / 30) * voyage_days,
        "Sertifikat": (sertifikat / 30) * voyage_days,
        "Depresiasi": ((depresiasi / 15) / 12 / 30) * voyage_days,
        "Other": other_cost
    }
else:
    biaya_mode = {"Charter Hire": (charter_hire / 30) * voyage_days, "Other": other_cost}

total_cost = sum(biaya_umum.values()) + sum(biaya_mode.values())
cost_per_mt = total_cost / total_cargo if total_cargo else 0

# ==============================
# Output
# ==============================
st.header("📊 Hasil Perhitungan")
st.write(f"🕒 Sailing Time (jam): {sailing_time:,.2f}")
st.write(f"📅 Voyage Days: {voyage_days:,.2f}")
st.write(f"🛢️ Total Consumption (liter): {total_consumption:,.0f}")

# ==============================
# Profit Skenario 0% - 50%
# ==============================
st.subheader("📈 Freight dengan Profit (0% - 50%)")
profit_list = []
for p in range(0, 55, 5):
    freight = cost_per_mt * (1 + p / 100)
    revenue = freight * total_cargo
    pph = revenue * 0.012
    net_profit = revenue - pph - total_cost
    profit_list.append([f"{p}%", f"Rp {freight:,.0f}", f"Rp {revenue:,.0f}", f"Rp {pph:,.0f}", f"Rp {net_profit:,.0f}"])

profit_df = pd.DataFrame(profit_list, columns=["Profit %", "Freight / MT", "Revenue", "PPh", "Net Profit"])
st.table(profit_df)

# ==============================
# PDF Export
# ==============================
def generate_pdf(profit_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT", styles["Title"]))
    elements.append(Spacer(1, 10))

    data_profit = [list(profit_df.columns)] + profit_df.values.tolist()
    table_profit = Table(data_profit, colWidths=[60, 90, 100, 100, 100])
    table_profit.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTSIZE", (0,0), (-1,-1), 8)
    ]))

    elements.append(Paragraph("📈 Skenario Profit (0% - 50%)", styles["Heading2"]))
    elements.append(table_profit)
    doc.build(elements)
    buffer.seek(0)
    return buffer

pdf_buffer = generate_pdf(profit_df)
st.download_button("📥 Download Laporan PDF", data=pdf_buffer, file_name="Freight_Report.pdf", mime="application/pdf")
