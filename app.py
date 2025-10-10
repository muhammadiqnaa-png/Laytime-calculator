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
    c.execute("PRAGMA table_info(kapal)")
    existing_cols = [row[1] for row in c.fetchall()]
    for col, dtype in required_cols.items():
        if col not in existing_cols:
            try:
                if col != "id":
                    c.execute(f"ALTER TABLE kapal ADD COLUMN {col} {dtype}")
            except Exception:
                pass
    conn.commit()
    conn.close()

def tambah_kapal(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO kapal (nama,total_cargo,consumption,angsuran,crew_cost,asuransi,docking,perawatan,sertifikat,depresiasi,charter_hire)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
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
        df = pd.DataFrame(columns=["id","nama","total_cargo","consumption","angsuran","crew_cost","asuransi","docking","perawatan","sertifikat","depresiasi","charter_hire"])
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
# Init App
# ==============================
st.set_page_config(page_title="Freight Calculator", layout="wide")
init_db()

# ==============================
# Simple Auth
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
# Sidebar Styling
# ==============================
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #1E293B;
        color: white;
        padding-top: 20px;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    .streamlit-expanderHeader {
        background-color: #334155 !important;
        color: #E2E8F0 !important;
        font-weight: 600;
        border-radius: 6px;
    }
    div.stButton > button {
        background-color: #0EA5E9 !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #38BDF8 !important;
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================
# Sidebar Components
# ==============================
st.sidebar.title("⚙️ Pengaturan Perhitungan")
st.sidebar.success(f"👤 Login sebagai: {st.session_state.username}")

with st.sidebar.expander("🚀 Mode Perhitungan"):
    mode = st.radio("Pilih Mode Biaya:", ["Owner", "Charter"])

with st.sidebar.expander("🛳️ Pilih Data Kapal"):
    df_kapal = get_all_kapal()
    kapal_names = df_kapal["nama"].dropna().tolist() if not df_kapal.empty else []
    kapal_list = ["-- Kapal Baru --"] + kapal_names
    pilihan_kapal = st.selectbox("Pilih Kapal", kapal_list)

kapal_data = None
if pilihan_kapal != "-- Kapal Baru --":
    row = get_kapal_by_name(pilihan_kapal)
    if row:
        _, nama, total_cargo_db, consumption_db, angsuran_db, crew_cost_db, asuransi_db, docking_db, perawatan_db, sertifikat_db, depresiasi_db, charter_hire_db = row + (None,) * (12 - len(row))
        kapal_data = dict(
            nama=nama,
            total_cargo=total_cargo_db,
            consumption=consumption_db,
            angsuran=angsuran_db,
            crew_cost=crew_cost_db,
            asuransi=asuransi_db,
            docking=docking_db,
            perawatan=perawatan_db,
            sertifikat=sertifikat_db,
            depresiasi=depresiasi_db,
            charter_hire=charter_hire_db
        )

with st.sidebar.expander("⚓ Parameter Kapal"):
    consumption = st.number_input("⚙️ Consumption (liter/jam)", value=float(kapal_data["consumption"]) if kapal_data and kapal_data.get("consumption") else 0.0)
    if mode == "Owner":
        angsuran = st.number_input("💰 Angsuran (Rp/bulan)", value=float(kapal_data["angsuran"]) if kapal_data and kapal_data.get("angsuran") else 0.0)
        crew_cost = st.number_input("👨‍✈️ Crew Cost (Rp/bulan)", value=float(kapal_data["crew_cost"]) if kapal_data and kapal_data.get("crew_cost") else 0.0)
        asuransi = st.number_input("🧾 Asuransi (Rp/bulan)", value=float(kapal_data["asuransi"]) if kapal_data and kapal_data.get("asuransi") else 0.0)
        docking = st.number_input("🛠️ Docking (Rp/bulan)", value=float(kapal_data["docking"]) if kapal_data and kapal_data.get("docking") else 0.0)
        perawatan = st.number_input("🔧 Perawatan (Rp/bulan)", value=float(kapal_data["perawatan"]) if kapal_data and kapal_data.get("perawatan") else 0.0)
        sertifikat = st.number_input("📜 Sertifikat (Rp/bulan)", value=float(kapal_data["sertifikat"]) if kapal_data and kapal_data.get("sertifikat") else 0.0)
        depresiasi = st.number_input("📉 Depresiasi (Rp/Beli)", value=float(kapal_data["depresiasi"]) if kapal_data and kapal_data.get("depresiasi") else 0.0)
    else:
        charter_hire = st.number_input("🚢 Charter Hire (Rp/bulan)", value=float(kapal_data["charter_hire"]) if kapal_data and kapal_data.get("charter_hire") else 0.0)

with st.sidebar.expander("🧭 Parameter Voyage"):
    speed_kosong = st.number_input("⚡ Speed Kosong (knot)", value=0.0)
    speed_isi = st.number_input("⚡ Speed Isi (knot)", value=0.0)
    harga_bunker = st.number_input("🛢️ Harga Bunker (Rp/liter)", value=0.0)
    harga_air_tawar = st.number_input("💧 Harga Air Tawar (Rp/Ton)", value=0.0)
    port_cost = st.number_input("⚓ Port Cost / Call (Rp)", value=0.0)
    asist_tug = st.number_input("🚤 Asist Tug (Rp)", value=0.0)
    premi_nm = st.number_input("🏷️ Premi (Rp/NM)", value=0.0)
    other_cost = st.number_input("📦 Other Cost (Rp)", value=0.0)
    port_stay = st.number_input("📅 Port Stay (Hari)", value=0.0)

with st.sidebar.expander("💾 Kelola Data Kapal"):
    nama_kapal_input = st.text_input("Nama Kapal", value=kapal_data["nama"] if kapal_data else "")
    total_cargo_input = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data and kapal_data.get("total_cargo") else 0.0)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Simpan / Update"):
            if not nama_kapal_input.strip():
                st.sidebar.error("Nama kapal tidak boleh kosong.")
            else:
                data = (
                    nama_kapal_input.strip(),
                    total_cargo_input,
                    consumption,
                    angsuran if mode == "Owner" else None,
                    crew_cost if mode == "Owner" else None,
                    asuransi if mode == "Owner" else None,
                    docking if mode == "Owner" else None,
                    perawatan if mode == "Owner" else None,
                    sertifikat if mode == "Owner" else None,
                    depresiasi if mode == "Owner" else None,
                    charter_hire if mode == "Charter" else None
                )
                tambah_kapal(data)
                st.sidebar.success("✅ Data kapal berhasil disimpan / diupdate!")
                st.rerun()
    with col2:
        if pilihan_kapal != "-- Kapal Baru --" and st.button("❌ Hapus"):
            hapus_kapal(nama_kapal_input.strip())
            st.sidebar.warning(f"Data kapal '{nama_kapal_input.strip()}' sudah dihapus.")
            st.rerun()
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.experimental_rerun()

# ==============================
# Input Voyage & Result Section
# ==============================
st.title("🚢 Freight Calculator Tongkang")

st.header("📥 Input Utama Voyage")
pol = st.text_input("Port of Loading (POL)")
pod = st.text_input("Port of Discharge (POD)")
total_cargo = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data and kapal_data.get("total_cargo") else 0.0)

jarak_laden = st.number_input("Jarak Laden (NM)", value=0.0)
jarak_ballast = st.number_input("Jarak Ballast (NM)", value=0.0)

sailing_time = (jarak_laden / speed_isi) + (jarak_ballast / speed_kosong) if speed_kosong > 0 and speed_isi > 0 else 0
voyage_days = (sailing_time / 24) + port_stay
total_consumption = (sailing_time * consumption) + (port_stay * consumption)

# --- Biaya
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
cost_per_mt = total_cost / total_cargo if total_cargo else 0

# --- Output
st.header("📊 Hasil Perhitungan")
st.write(f"Sailing Time (jam): {sailing_time:,.2f}")
st.write(f"Total Voyage Days: {voyage_days:,.2f}")
st.write(f"Total Consumption (liter): {total_consumption:,.0f}")

st.subheader(f"💰 Biaya Mode ({mode})")
for k, v in biaya_mode.items():
    st.write(f"- {k}: Rp {v:,.0f}")

st.subheader("💰 Biaya Umum")
for k, v in biaya_umum.items():
    st.write(f"- {k}: Rp {v:,.0f}")

st.subheader("🧮 Total Cost")
st.write(f"TOTAL COST: Rp {total_cost:,.0f}")
st.subheader("🧮 Cost per MT")
st.write(f"FREIGHT: Rp {cost_per_mt:,.0f} / MT")

# --- Profit Table
st.subheader("📈 Freight dengan Profit (0% - 50%)")
profit_list = []
for p in range(0,55,5):
    freight = cost_per_mt * (1 + p/100)
    revenue = freight * total_cargo
    Pph = revenue * 0.012
    net_profit = revenue - Pph - total_cost
    profit_list.append([f"{p}%", f"Rp {freight:,.0f}", f"Rp {revenue:,.0f}", f"Rp {Pph:,.0f}", f"Rp {net_profit:,.0f}"])
profit_df = pd.DataFrame(profit_list, columns=["Profit %","Freight / MT","Revenue","Pph","Net Profit"])
st.table(profit_df)

# --- PDF Export
input_data = [
    ["POL", pol],
    ["POD", pod],
    ["Jarak Laden (NM)", f"{jarak_laden:,}"],
    ["Jarak Ballast (NM)", f"{jarak_ballast:,}"],
    ["Total Cargo (MT)", f"{total_cargo:,}"],
    ["Voyage Days", f"{voyage_days:,.2f} hari"]
]

results = list(biaya_mode.items()) + list(biaya_umum.items())
results.append(["TOTAL COST", total_cost])
results.append(["Cost per MT", cost_per_mt])

def generate_pdf(input_data, results, profit_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    style_title = styles["Title"]; style_title.fontSize = 14
    style_heading = styles["Heading2"]; style_heading.fontSize = 11
    style_normal = styles["Normal"]; style_normal.fontSize = 9

    elements.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT", style_title))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Input Utama", style_heading))
    table_input = Table(input_data, colWidths=[150, 300])
    table_input.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 9)
    ]))
    elements.append(table_input)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Hasil Perhitungan", style_heading))
    table_results = Table([[k, f"Rp {v:,.0f}" if isinstance(v, (int,float)) else v] for k,v in results],
                          colWidths=[200,250])
    table_results.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),9)
    ]))
    elements.append(table_results)
    elements.append(Spacer(1,10))

    elements.append(Paragraph("Skenario Profit (0%-50%)", style_heading))
    data_profit = [list(profit_df.columns)] + profit_df.values.tolist()
    table_profit = Table(data_profit, colWidths=[60,90,100,100,100])
    table_profit.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("FONTSIZE",(0,0),(-1,-1),8
    
