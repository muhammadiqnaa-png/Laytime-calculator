import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import requests
import os

# ---------- CONFIG ----------
BACKEND = st.secrets.get("backend_url", "https://my-backend.onrender.com")
DB_PATH = "data.db"
# ----------------------------

# ==============================
# Database Setup (kapal)
# ==============================
def init_db_kapal():
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
                if col == "id":
                    continue
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

init_db_kapal()

# ==============================
# AUTH LOGIN / REGISTER
# ==============================
st.set_page_config(page_title="Freight Calculator", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login / Daftar — Freight Calculator")
    tab1, tab2 = st.tabs(["Login", "Daftar Baru"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            try:
                r = requests.post(f"{BACKEND}/login", json={"email": email, "password": password}, timeout=10)
                if r.status_code == 200:
                    st.session_state.logged_in = True
                    st.session_state.email = email
                    st.session_state.username = email.split("@")[0]
                    st.success("Login berhasil!")
                    st.experimental_rerun()
                else:
                    st.error("Login gagal, periksa kembali email dan password.")
            except Exception as e:
                st.error(f"Gagal hubungi backend: {e}")
    with tab2:
        email_r = st.text_input("Email", key="reg_email")
        password_r = st.text_input("Password", type="password", key="reg_pw")
        password_r2 = st.text_input("Konfirmasi Password", type="password", key="reg_pw2")
        if st.button("Daftar"):
            if not email_r or not password_r:
                st.error("Email dan password wajib diisi.")
            elif password_r != password_r2:
                st.error("Password konfirmasi tidak cocok.")
            else:
                try:
                    r = requests.post(f"{BACKEND}/register", json={"email": email_r, "password": password_r}, timeout=10)
                    if r.status_code == 200:
                        st.success("Registrasi berhasil! Silakan login.")
                    else:
                        st.error("Gagal registrasi.")
                except Exception as e:
                    st.error(f"Gagal hubungi backend: {e}")
    st.stop()

# ==============================
# MAIN APP (setelah login)
# ==============================
st.sidebar.success(f"Login sebagai: {st.session_state.email}")
st.title("🚢 Freight Calculator Tongkang")

# Sidebar - kapal settings
st.sidebar.title("⚙️ Pengaturan Perhitungan")

mode = st.sidebar.radio("Pilih Mode Biaya:", ["Owner", "Charter"])

df_kapal = get_all_kapal()
kapal_names = df_kapal["nama"].dropna().tolist() if not df_kapal.empty else []
kapal_list = ["-- Kapal Baru --"] + kapal_names
pilihan_kapal = st.sidebar.selectbox("Pilih Kapal", kapal_list)

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

st.sidebar.markdown("### 📦 Data Kapal")
if kapal_data:
    st.sidebar.write(f"**Kapal:** {kapal_data.get('nama')}")
else:
    st.sidebar.info("Pilih kapal atau buat kapal baru.")

# Input form kapal
consumption = st.sidebar.number_input("Consumption (liter/jam)", value=float(kapal_data["consumption"]) if kapal_data else 120)
if mode == "Owner":
    angsuran = st.sidebar.number_input("Angsuran (Rp/bulan)", value=float(kapal_data["angsuran"]) if kapal_data else 750000000)
    crew_cost = st.sidebar.number_input("Crew Cost (Rp/bulan)", value=float(kapal_data["crew_cost"]) if kapal_data else 60000000)
    asuransi = st.sidebar.number_input("Asuransi (Rp/bulan)", value=float(kapal_data["asuransi"]) if kapal_data else 50000000)
    docking = st.sidebar.number_input("Docking (Rp/bulan)", value=float(kapal_data["docking"]) if kapal_data else 50000000)
    perawatan = st.sidebar.number_input("Perawatan (Rp/bulan)", value=float(kapal_data["perawatan"]) if kapal_data else 50000000)
    sertifikat = st.sidebar.number_input("Sertifikat (Rp/bulan)", value=float(kapal_data["sertifikat"]) if kapal_data else 50000000)
    depresiasi = st.sidebar.number_input("Depresiasi (Rp/Beli)", value=float(kapal_data["depresiasi"]) if kapal_data else 45000000000)
else:
    charter_hire = st.sidebar.number_input("Charter Hire (Rp/bulan)", value=float(kapal_data["charter_hire"]) if kapal_data else 750000000)

st.sidebar.markdown("### ⚓ Parameter Voyage")
speed_kosong = st.sidebar.number_input("Speed Kosong (knot)", value=3.0)
speed_isi = st.sidebar.number_input("Speed Isi (knot)", value=4.0)
harga_bunker = st.sidebar.number_input("Harga Bunker (Rp/liter)", value=12500)
harga_air_tawar = st.sidebar.number_input("Harga Air Tawar (Rp/Ton)", value=120000)
port_cost = st.sidebar.number_input("Port cost/call (Rp)", value=50000000)
asist_tug = st.sidebar.number_input("Asist Tug (Rp)", value=35000000)
premi_nm = st.sidebar.number_input("Premi (Rp/NM)", value=50000)
other_cost = st.sidebar.number_input("Other Cost (Rp)", value=50000000)
port_stay = st.sidebar.number_input("Port Stay (Hari)", value=10)

# Simpan / Hapus Kapal
with st.sidebar.expander("💾 Kelola Kapal"):
    nama_kapal_input = st.text_input("Nama Kapal", value=kapal_data["nama"] if kapal_data else "")
    total_cargo_input = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data else 7500)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simpan / Update"):
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
            st.sidebar.success("✅ Data kapal disimpan.")
            st.rerun()
    with col2:
        if pilihan_kapal != "-- Kapal Baru --" and st.button("❌ Hapus"):
            hapus_kapal(nama_kapal_input.strip())
            st.sidebar.warning("Kapal dihapus.")
            st.rerun()

# ==============================
# Main voyage calculation
# ==============================
st.header("📥 Input Utama Voyage")
pol = st.text_input("Port of Loading (POL)")
pod = st.text_input("Port of Discharge (POD)")
total_cargo = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data else 7500)
jarak = st.number_input("Jarak (NM)", value=630)

sailing_time = (jarak / speed_kosong) + (jarak / speed_isi)
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
    biaya_mode = {"Charter Hire": (charter_hire / 30) * voyage_days, "Other": other_cost}

total_cost = sum(biaya_umum.values()) + sum(biaya_mode.values())
cost_per_mt = total_cost / total_cargo if total_cargo else 0

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

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.session_state.username = ""
    st.rerun()
