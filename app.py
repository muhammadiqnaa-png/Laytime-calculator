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
# Database Setup (auto update)
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Buat tabel kapal kalau belum ada
    c.execute("""
        CREATE TABLE IF NOT EXISTS kapal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE
        )
    """)

    # Tambah kolom baru kalau belum ada
    required_cols = {
        "total_cargo": "REAL",
        "consumption": "REAL",
        "angsuran": "REAL",
        "crew_cost": "REAL",
        "asuransi": "REAL",
        "docking": "REAL",
        "perawatan": "REAL",
        "sertifikat": "REAL",
        "depresiasi": "REAL",
        "charter_hire": "REAL",
        "speed_isi": "REAL",
        "speed_kosong": "REAL",
        "consumption_isi": "REAL",
        "consumption_kosong": "REAL",
        "consumption_port": "REAL",
        "daily_cost": "REAL"
    }

    c.execute("PRAGMA table_info(kapal)")
    existing_cols = [row[1] for row in c.fetchall()]
    for col, dtype in required_cols.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE kapal ADD COLUMN {col} {dtype}")

    conn.commit()
    conn.close()


def tambah_kapal(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO kapal (
            nama, total_cargo, consumption, angsuran, crew_cost, asuransi, docking,
            perawatan, sertifikat, depresiasi, charter_hire,
            speed_isi, speed_kosong, consumption_isi, consumption_kosong, consumption_port, daily_cost
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, data)
    conn.commit()
    conn.close()


def hapus_kapal(nama):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM kapal WHERE nama=?", (nama,))
    conn.commit()
    conn.close()


def get_all_kapal():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM kapal", conn)
    except Exception:
        df = pd.DataFrame()
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
# APP SETUP
# ==============================
st.set_page_config(page_title="Freight Calculator", layout="wide")
init_db()

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
            st.rerun()
        else:
            st.error("Username / password salah")
    st.stop()

st.sidebar.success(f"Login sebagai: {st.session_state.username}")
st.title("🚢 Freight Calculator Tongkang")

# ==============================
# SIDEBAR - Pengaturan & Parameter
# ==============================
st.sidebar.title("⚙️ Pengaturan")

mode = st.sidebar.radio("Mode Biaya:", ["Owner", "Charter"])
df_kapal = get_all_kapal()
kapal_list = ["-- Kapal Baru --"] + df_kapal["nama"].dropna().tolist() if not df_kapal.empty else ["-- Kapal Baru --"]
pilihan_kapal = st.sidebar.selectbox("Pilih Kapal", kapal_list)

kapal_data = None
if pilihan_kapal != "-- Kapal Baru --":
    row = get_kapal_by_name(pilihan_kapal)
    if row:
        columns = [col for col in df_kapal.columns]
        kapal_data = dict(zip(columns, row))

# Sidebar untuk parameter umum
st.sidebar.markdown("### 📦 Data Kapal")
total_cargo_input = st.sidebar.number_input(
    "Total Cargo (MT)",
    value=float(kapal_data["total_cargo"]) if kapal_data and "total_cargo" in kapal_data else 0.0
)
consumption = st.sidebar.number_input("Consumption (liter/jam)", value=float(kapal_data.get("consumption", 0)))

# Parameter Voyage
st.sidebar.markdown("### ⚓ Parameter Voyage")
harga_bunker = st.sidebar.number_input("Harga Bunker (Rp/liter)", value=0.0)
harga_air_tawar = st.sidebar.number_input("Harga Air Tawar (Rp/Ton)", value=0.0)
port_cost = st.sidebar.number_input("Port cost/call (Rp)", value=0.0)
asist_tug = st.sidebar.number_input("Asist Tug (Rp)", value=0.0)
premi_nm = st.sidebar.number_input("Premi (Rp/NM)", value=0.0)
other_cost = st.sidebar.number_input("Other Cost (Rp)", value=0.0)
port_stay = st.sidebar.number_input("Port Stay (hari)", value=0.0)

# Biaya Mode
st.sidebar.markdown("### 💰 Biaya Mode")
if mode == "Owner":
    angsuran = st.sidebar.number_input("Angsuran (Rp/bulan)", value=0.0)
    crew_cost = st.sidebar.number_input("Crew Cost (Rp/bulan)", value=0.0)
    asuransi = st.sidebar.number_input("Asuransi (Rp/bulan)", value=0.0)
    docking = st.sidebar.number_input("Docking (Rp/bulan)", value=0.0)
    perawatan = st.sidebar.number_input("Perawatan (Rp/bulan)", value=0.0)
    sertifikat = st.sidebar.number_input("Sertifikat (Rp/bulan)", value=0.0)
    depresiasi = st.sidebar.number_input("Depresiasi (Rp)", value=0.0)
else:
    charter_hire = st.sidebar.number_input("Charter Hire (Rp/bulan)", value=0.0)

# ==============================
# INPUT MAIN
# ==============================
st.header("📥 Input Voyage")
pol = st.text_input("Port of Loading (POL)")
pod = st.text_input("Port of Discharge (POD)")
jarak_laden = st.number_input("Jarak Laden (NM)", value=0.0)
jarak_ballast = st.number_input("Jarak Ballast (NM)", value=0.0)

# ==============================
# PERHITUNGAN
# ==============================
sailing_time = (
    (jarak_laden / speed_isi if speed_isi else 0)
    + (jarak_ballast / speed_kosong if speed_kosong else 0)
)
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
    biaya_mode = {
        "Charter Hire": (charter_hire / 30) * voyage_days,
        "Other": other_cost
    }

total_cost = sum(biaya_umum.values()) + sum(biaya_mode.values())
cost_per_mt = total_cost / total_cargo_input if total_cargo_input else 0

# ==============================
# OUTPUT
# ==============================
st.header("📊 Hasil Perhitungan")
st.write(f"Sailing Time (jam): {sailing_time:,.2f}")
st.write(f"Voyage Days: {voyage_days:,.2f}")
st.write(f"Total Consumption (liter): {total_consumption:,.0f}")

st.subheader(f"💰 Biaya Mode ({mode})")
for k, v in biaya_mode.items():
    st.write(f"- {k}: Rp {v:,.0f}")

st.subheader("💰 Biaya Umum")
for k, v in biaya_umum.items():
    st.write(f"- {k}: Rp {v:,.0f}")

st.subheader("🧮 Total Cost")
st.write(f"TOTAL COST: Rp {total_cost:,.0f}")
st.write(f"FREIGHT: Rp {cost_per_mt:,.0f} / MT")

# ==============================
# PROFIT SCENARIO
# ==============================
st.subheader("📈 Freight dengan Profit (0% - 50%)")
profit_list = []
for p in range(0, 55, 5):
    freight = cost_per_mt * (1 + p / 100)
    revenue = freight * total_cargo_input
    Pph = revenue * 0.012
    net_profit = revenue - Pph - total_cost
    profit_list.append([f"{p}%", f"Rp {freight:,.0f}", f"Rp {revenue:,.0f}", f"Rp {Pph:,.0f}", f"Rp {net_profit:,.0f}"])
profit_df = pd.DataFrame(profit_list, columns=["Profit %", "Freight / MT", "Revenue", "Pph", "Net Profit"])
st.table(profit_df)

# ==============================
# PDF EXPORT
# ==============================
def generate_pdf(input_data, results, profit_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT", styles["Title"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Input Utama", styles["Heading2"]))
    table_input = Table(input_data, colWidths=[150, 300])
    table_input.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9)
    ]))
    elements.append(table_input)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Hasil Perhitungan", styles["Heading2"]))
    table_results = Table(results, colWidths=[200, 250])
    table_results.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9)
    ]))
    elements.append(table_results)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Skenario Profit", styles["Heading2"]))
    data_profit = [list(profit_df.columns)] + profit_df.values.tolist()
    table_profit = Table(data_profit, colWidths=[60, 90, 100, 100, 100])
    table_profit.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER")
    ]))
    elements.append(table_profit)

    doc.build(elements)
    buffer.seek(0)
    return buffer

input_data = [
    ["POL", pol], ["POD", pod],
    ["Jarak Laden (NM)", jarak_laden],
    ["Jarak Ballast (NM)", jarak_ballast],
    ["Voyage Days", f"{voyage_days:,.2f}"]
]
results = list(biaya_mode.items()) + list(biaya_umum.items()) + [["TOTAL COST", total_cost], ["Cost per MT", cost_per_mt]]
pdf_buffer = generate_pdf(input_data, results, profit_df)

st.download_button("📥 Download Laporan PDF", data=pdf_buffer, file_name=f"Freight_Report_{pol or 'POL'}_{pod or 'POD'}.pdf", mime="application/pdf")

st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()
