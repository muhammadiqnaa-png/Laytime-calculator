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
            nama TEXT UNIQUE,
            total_cargo REAL,
            consumption REAL,
            angsuran REAL,
            crew_cost REAL,
            asuransi REAL,
            docking REAL,
            perawatan REAL,
            sertifikat REAL,
            depresiasi REAL,
            charter_hire REAL
        )
    """)
    conn.commit()
    conn.close()

def tambah_kapal(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO kapal 
        (nama,total_cargo,consumption,angsuran,crew_cost,asuransi,docking,perawatan,sertifikat,depresiasi,charter_hire)
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

# ==============================
# Sidebar Settings
# ==============================
st.sidebar.success(f"Login sebagai: {st.session_state.username}")
st.sidebar.title("⚙️ Pengaturan Perhitungan")

mode = st.sidebar.radio("Pilih Mode Biaya:", ["Owner", "Charter"])

df_kapal = get_all_kapal()
kapal_list = ["-- Kapal Baru --"] + df_kapal["nama"].dropna().tolist()
pilihan_kapal = st.sidebar.selectbox("Pilih Kapal", kapal_list)

kapal_data = None
if pilihan_kapal != "-- Kapal Baru --":
    row = get_kapal_by_name(pilihan_kapal)
    if row:
        _, nama, total_cargo_db, consumption_db, angsuran_db, crew_cost_db, asuransi_db, docking_db, perawatan_db, sertifikat_db, depresiasi_db, charter_hire_db = row
        kapal_data = {
            "nama": nama,
            "total_cargo": total_cargo_db or 0,
            "consumption": consumption_db or 0,
            "angsuran": angsuran_db or 0,
            "crew_cost": crew_cost_db or 0,
            "asuransi": asuransi_db or 0,
            "docking": docking_db or 0,
            "perawatan": perawatan_db or 0,
            "sertifikat": sertifikat_db or 0,
            "depresiasi": depresiasi_db or 0,
            "charter_hire": charter_hire_db or 0
        }

# ------------------------------
# Input di Sidebar
# ------------------------------
st.sidebar.markdown("### ⚓ Parameter Kapal")
nama_kapal_input = st.sidebar.text_input("Nama Kapal", value=kapal_data["nama"] if kapal_data else "")
total_cargo_input = st.sidebar.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data else 0.0)
consumption = st.sidebar.number_input("Consumption (liter/jam)", value=float(kapal_data["consumption"]) if kapal_data else 0.0)

if mode == "Owner":
    angsuran = st.sidebar.number_input("Angsuran (Rp/bulan)", value=float(kapal_data["angsuran"]) if kapal_data else 0.0)
    crew_cost = st.sidebar.number_input("Crew Cost (Rp/bulan)", value=float(kapal_data["crew_cost"]) if kapal_data else 0.0)
    asuransi = st.sidebar.number_input("Asuransi (Rp/bulan)", value=float(kapal_data["asuransi"]) if kapal_data else 0.0)
    docking = st.sidebar.number_input("Docking (Rp/bulan)", value=float(kapal_data["docking"]) if kapal_data else 0.0)
    perawatan = st.sidebar.number_input("Perawatan (Rp/bulan)", value=float(kapal_data["perawatan"]) if kapal_data else 0.0)
    sertifikat = st.sidebar.number_input("Sertifikat (Rp/bulan)", value=float(kapal_data["sertifikat"]) if kapal_data else 0.0)
    depresiasi = st.sidebar.number_input("Depresiasi (Rp/Beli)", value=float(kapal_data["depresiasi"]) if kapal_data else 0.0)
else:
    charter_hire = st.sidebar.number_input("Charter Hire (Rp/bulan)", value=float(kapal_data["charter_hire"]) if kapal_data else 0.0)

st.sidebar.markdown("### ⚙️ Parameter Voyage")
speed_kosong = st.sidebar.number_input("Speed Kosong (knot)", value=0.0)
speed_isi = st.sidebar.number_input("Speed Isi (knot)", value=0.0)
harga_bunker = st.sidebar.number_input("Harga Bunker (Rp/liter)", value=0.0)
harga_air_tawar = st.sidebar.number_input("Harga Air Tawar (Rp/Ton)", value=0.0)
port_cost = st.sidebar.number_input("Port Cost/call (Rp)", value=0.0)
asist_tug = st.sidebar.number_input("Asist Tug (Rp)", value=0.0)
premi_nm = st.sidebar.number_input("Premi (Rp/NM)", value=0.0)
other_cost = st.sidebar.number_input("Other Cost (Rp)", value=0.0)
port_stay = st.sidebar.number_input("Port Stay (Hari)", value=0.0)

# Simpan/Hapus
with st.sidebar.expander("💾 Kelola Data Kapal"):
    if st.button("Simpan / Update"):
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
            st.sidebar.success("✅ Data kapal berhasil disimpan!")
            st.rerun()
    if pilihan_kapal != "-- Kapal Baru --" and st.button("❌ Hapus Kapal"):
        hapus_kapal(nama_kapal_input.strip())
        st.sidebar.warning("Data kapal dihapus.")
        st.rerun()

# ==============================
# Main Section
# ==============================
st.title("🚢 Freight Calculator Tongkang")

pol = st.text_input("Port of Loading (POL)")
pod = st.text_input("Port of Discharge (POD)")
jarak = st.number_input("Jarak (NM)", value=0.0)

if total_cargo_input and speed_kosong and speed_isi:
    sailing_time = (jarak / speed_isi) + (jarak / speed_kosong)
else:
    sailing_time = 0

voyage_days = (sailing_time / 24) + port_stay
total_consumption = (sailing_time * consumption) + (port_stay * consumption)

biaya_umum = {
    "Bunker BBM": total_consumption * harga_bunker,
    "Air Tawar": (voyage_days * 2) * harga_air_tawar,
    "Port Cost": port_cost * 2,
    "Premi": premi_nm * jarak,
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

st.header("📊 Hasil Perhitungan")
st.write(f"Sailing Time (jam): {sailing_time:,.2f}")
st.write(f"Voyage Days: {voyage_days:,.2f}")
st.write(f"Total Consumption (liter): {total_consumption:,.0f}")
st.write(f"Total Cost: Rp {total_cost:,.0f}")
st.write(f"Cost per MT: Rp {cost_per_mt:,.0f}")

# PDF export same
input_data = [["POL", pol], ["POD", pod], ["Jarak (NM)", f"{jarak:,}"], ["Total Cargo (MT)", f"{total_cargo_input:,}"], ["Voyage Days", f"{voyage_days:,.2f} hari"]]
results = list(biaya_mode.items()) + list(biaya_umum.items())
results.append(["TOTAL COST", total_cost])
results.append(["Cost per MT", cost_per_mt])

def generate_pdf(input_data, results):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("LAPORAN PERHITUNGAN FREIGHT", styles["Title"])]
    elements.append(Table(input_data))
    elements.append(Spacer(1, 10))
    elements.append(Table([[k, f"Rp {v:,.0f}"] for k, v in results]))
    doc.build(elements)
    buffer.seek(0)
    return buffer

pdf_buffer = generate_pdf(input_data, results)
st.download_button("📥 Download PDF", data=pdf_buffer, file_name="Freight_Report.pdf", mime="application/pdf")

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()
