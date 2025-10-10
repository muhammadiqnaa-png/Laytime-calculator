# app.py
import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ------------------------------
# Config & DB path
# ------------------------------
DB_PATH = "data.db"
st.set_page_config(page_title="Freight Calculator Tongkang", page_icon="⚓", layout="wide")

# ------------------------------
# Database helpers (safe auto-alter)
# ------------------------------
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
    # create table baseline
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS kapal (
            {", ".join([f"{col} {dtype}" for col, dtype in required_cols.items()])}
        )
    """)
    # ensure missing columns added (safe)
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
    # Insert or replace by nama (UNIQUE) — use simple approach: delete then insert to keep unique constraint safe
    try:
        c.execute("DELETE FROM kapal WHERE nama = ?", (data[0],))
    except Exception:
        pass
    c.execute("""
        INSERT INTO kapal (nama,total_cargo,consumption,angsuran,crew_cost,asuransi,docking,perawatan,sertifikat,depresiasi,charter_hire)
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

# init db
init_db()

# ------------------------------
# Simple auth (kept small)
# ------------------------------
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

# ------------------------------
# Sidebar styling (dark-like)
# ------------------------------
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {background-color: #0f172a;}
    [data-testid="stSidebar"] .st-expander {background-color: #0b1220;}
    .css-1d391kg, .css-1v3fvcr, h1, h2, h3, h4 {color: #f8fafc !important;}
    .stButton>button {background-color:#0ea5e9;color:white;border-radius:6px;}
    .stButton>button:hover {background-color:#38bdf8;color:black;}
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------
# Sidebar: grouped expanders
# ------------------------------
with st.sidebar:
    st.sidebar.success(f"👤 Login sebagai: {st.session_state.username}")
    st.sidebar.title("⚙️ Pengaturan Perhitungan")

    # Mode & Kapal picker
    with st.sidebar.expander("🧭 Mode & Kapal", expanded=True):
        mode = st.selectbox("Mode Perhitungan", ["Owner", "Charter"])
        kapal_choice = st.selectbox("Pilih Kapal (DB)", ["-- Kapal Baru --"] + get_all_kapal()["nama"].fillna("").tolist())
        kapal_name_input = st.text_input("Nama Kapal (untuk simpan)", value="" if kapal_choice == "-- Kapal Baru --" else kapal_choice)

    # Data kapal (saved)
    with st.sidebar.expander("📦 Data Kapal (Default / Tersimpan)"):
        if kapal_choice != "-- Kapal Baru --":
            row = get_kapal_by_name(kapal_choice)
            if row:
                # unpack safely
                _, _nama, _total_cargo_db, _consumption_db, _angsuran_db, _crew_cost_db, _asuransi_db, _docking_db, _perawatan_db, _sertifikat_db, _depresiasi_db, _charter_hire_db = row + (None,) * (12 - len(row))
            else:
                _nama = ""
                _total_cargo_db = _consumption_db = _angsuran_db = _crew_cost_db = _asuransi_db = _docking_db = _perawatan_db = _sertifikat_db = _depresiasi_db = _charter_hire_db = None
        else:
            _nama = ""
            _total_cargo_db = _consumption_db = _angsuran_db = _crew_cost_db = _asuransi_db = _docking_db = _perawatan_db = _sertifikat_db = _depresiasi_db = _charter_hire_db = None

        st.write("Nama kapal tersimpan:", _nama or "-")
        st.write("Total Cargo (MT):", f"{_total_cargo_db:,}" if _total_cargo_db else "-")
        st.write("Consumption (L/jam):", f"{_consumption_db:,}" if _consumption_db else "-")

    # Parameter kapal (editable, defaults 0)
    with st.sidebar.expander("⚓ Parameter Kapal (Editable)"):
        total_cargo = st.number_input("Total Cargo (MT)", value=float(_total_cargo_db) if _total_cargo_db is not None else 0.0)
        consumption = st.number_input("Consumption (liter/jam)", value=float(_consumption_db) if _consumption_db is not None else 0.0)

        if mode == "Owner":
            angsuran = st.number_input("Angsuran (Rp/bulan)", value=float(_angsuran_db) if _angsuran_db is not None else 0.0)
            crew_cost = st.number_input("Crew Cost (Rp/bulan)", value=float(_crew_cost_db) if _crew_cost_db is not None else 0.0)
            asuransi = st.number_input("Asuransi (Rp/bulan)", value=float(_asuransi_db) if _asuransi_db is not None else 0.0)
            docking = st.number_input("Docking (Rp/bulan)", value=float(_docking_db) if _docking_db is not None else 0.0)
            perawatan = st.number_input("Perawatan (Rp/bulan)", value=float(_perawatan_db) if _perawatan_db is not None else 0.0)
            sertifikat = st.number_input("Sertifikat (Rp/bulan)", value=float(_sertifikat_db) if _sertifikat_db is not None else 0.0)
            depresiasi = st.number_input("Depresiasi / Harga Kapal (Rp)", value=float(_depresiasi_db) if _depresiasi_db is not None else 0.0)
        else:
            charter_hire = st.number_input("Charter Hire (Rp/bulan)", value=float(_charter_hire_db) if _charter_hire_db is not None else 0.0)

    # Voyage params
    with st.sidebar.expander("🧭 Parameter Voyage"):
        pol = st.text_input("Port of Loading (POL)", value="")
        pod = st.text_input("Port of Discharge (POD)", value="")
        jarak_laden = st.number_input("Jarak Laden (NM)", value=0.0)
        jarak_ballast = st.number_input("Jarak Ballast (NM)", value=0.0)
        speed_isi = st.number_input("Speed Isi (knot)", value=0.0)
        speed_kosong = st.number_input("Speed Kosong (knot)", value=0.0)
        harga_bunker = st.number_input("Harga Bunker (Rp/liter)", value=0.0)
        harga_air_tawar = st.number_input("Harga Air Tawar (Rp/Ton)", value=0.0)
        port_cost = st.number_input("Port Cost / Call (Rp)", value=0.0)
        premi_nm = st.number_input("Premi (Rp/NM)", value=0.0)
        asist_tug = st.number_input("Asist Tug (Rp)", value=0.0)
        other_cost = st.number_input("Other Cost (Rp)", value=0.0)
        port_stay = st.number_input("Port Stay (Hari)", value=0.0)

    # Kelola kapal (save/update/delete)
    with st.sidebar.expander("💾 Kelola Data Kapal"):
        nama_kapal_save = st.text_input("Nama Kapal untuk simpan", value=kapal_name_input or "")
        total_cargo_save = st.number_input("Total Cargo (MT) - simpan", value=float(total_cargo))
        consumption_save = st.number_input("Consumption (L/jam) - simpan", value=float(consumption))
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("💾 Simpan / Update Kapal"):
                data = (
                    nama_kapal_save.strip() or kapal_name_input.strip() or "Unnamed",
                    total_cargo_save,
                    consumption_save,
                    angsuran if mode == "Owner" else None,
                    crew_cost if mode == "Owner" else None,
                    asuransi if mode == "Owner" else None,
                    docking if mode == "Owner" else None,
                    perawatan if mode == "Owner" else None,
                    sertifikat if mode == "Owner" else None,
                    depresiasi if mode == "Owner" else None,
                    charter_hire if mode != "Owner" else None
                )
                tambah_kapal(data)
                st.success("✅ Data kapal tersimpan / diupdate.")
        with col2:
            if st.button("❌ Hapus Kapal Tersimpan"):
                if kapal_choice != "-- Kapal Baru --":
                    hapus_kapal(kapal_choice)
                    st.warning(f"Data kapal '{kapal_choice}' sudah dihapus.")
                else:
                    st.error("Pilih kapal tersimpan untuk dihapus.")

    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

# ------------------------------
# Main page: calculations & output
# ------------------------------
st.title("🚢 Freight Calculator Tongkang")
st.header("📊 Hasil Perhitungan")

# compute safely
jarak_total = jarak_laden + jarak_ballast
# sailing_time: if speeds positive; otherwise 0
if speed_isi > 0 and speed_kosong > 0:
    sailing_time = (jarak_laden / speed_isi) + (jarak_ballast / speed_kosong)
else:
    sailing_time = 0.0
voyage_days = (sailing_time / 24.0) + port_stay
total_consumption = (sailing_time * consumption) + (port_stay * consumption)

# biaya umum & mode
biaya_umum = {
    "Bunker BBM": total_consumption * harga_bunker,
    "Air Tawar": (voyage_days * 2) * harga_air_tawar,
    "Port Cost": port_cost * 2,
    "Premi": premi_nm * jarak_total,
    "Asist Tug": asist_tug
}

if mode == "Owner":
    biaya_mode = {
        "Angsuran": (angsuran / 30.0) * voyage_days,
        "Crew Cost": (crew_cost / 30.0) * voyage_days,
        "Asuransi": (asuransi / 30.0) * voyage_days,
        "Docking": (docking / 30.0) * voyage_days,
        "Perawatan": (perawatan / 30.0) * voyage_days,
        "Sertifikat": (sertifikat / 30.0) * voyage_days,
        "Depresiasi": ((depresiasi / 15.0) / 12.0 / 30.0) * voyage_days,
        "Other": other_cost
    }
else:
    biaya_mode = {
        "Charter Hire": (charter_hire / 30.0) * voyage_days,
        "Other": other_cost
    }

total_cost = sum(biaya_umum.values()) + sum(biaya_mode.values())
cost_per_mt = total_cost / total_cargo if total_cargo and total_cargo > 0 else 0.0

# display metrics
c1, c2, c3 = st.columns(3)
c1.metric("Sailing Time (jam)", f"{sailing_time:,.2f}")
c2.metric("Voyage Days", f"{voyage_days:,.2f}")
c3.metric("Total Consumption (liter)", f"{total_consumption:,.0f}")

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

# profit scenario table
st.subheader("📈 Freight dengan Profit (0% - 50%)")
profit_list = []
for p in range(0, 55, 5):
    freight = cost_per_mt * (1 + p / 100.0)
    revenue = freight * total_cargo
    pph = revenue * 0.012
    net_profit = revenue - pph - total_cost
    profit_list.append([f"{p}%", f"{freight:,.0f}", f"{revenue:,.0f}", f"{pph:,.0f}", f"{net_profit:,.0f}"])
profit_df = pd.DataFrame(profit_list, columns=["Profit %", "Freight/MT (Rp)", "Revenue (Rp)", "PPh (Rp)", "Net Profit (Rp)"])
st.dataframe(profit_df, use_container_width=True)

# ------------------------------
# PDF generation (full report: inputs, biaya, profit)
# ------------------------------
def format_rp(x):
    try:
        return f"Rp {x:,.0f}"
    except Exception:
        return str(x)

def generate_pdf_report():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=18, leftMargin=18,
                            topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal = styles["Normal"]
    normal.fontSize = 9

    elements = []
    elements.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT TONGKANG", title_style))
    elements.append(Spacer(1, 8))

    # Input Utama table
    elements.append(Paragraph("Input Utama", heading_style))
    input_table = [
        ["POL", pol or "-"],
        ["POD", pod or "-"],
        ["Total Cargo (MT)", f"{total_cargo:,.0f}"],
        ["Jarak Laden (NM)", f"{jarak_laden:,.2f}"],
        ["Jarak Ballast (NM)", f"{jarak_ballast:,.2f}"],
        ["Total Jarak (NM)", f"{jarak_total:,.2f}"],
        ["Speed Isi (knot)", f"{speed_isi:,.2f}"],
        ["Speed Kosong (knot)", f"{speed_kosong:,.2f}"],
        ["Port Stay (hari)", f"{port_stay:,.2f}"],
        ["Consumption (L/jam)", f"{consumption:,.2f}"]
    ]
    t = Table(input_table, colWidths=[150, 330])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # Hasil Perhitungan
    elements.append(Paragraph("Hasil Perhitungan", heading_style))
    result_table = [
        ["Sailing Time (jam)", f"{sailing_time:,.2f}"],
        ["Voyage Days", f"{voyage_days:,.2f}"],
        ["Total Consumption (liter)", f"{total_consumption:,.0f}"],
        ["Total Cost (Rp)", format_rp(total_cost)],
        ["Cost per MT (Rp)", format_rp(cost_per_mt)]
    ]
    tr = Table(result_table, colWidths=[150, 330])
    tr.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elements.append(tr)
    elements.append(Spacer(1, 10))

    # Biaya Mode
    elements.append(Paragraph("Biaya Mode", heading_style))
    mode_rows = [["Item", "Rp"]] + [[k, format_rp(v)] for k, v in biaya_mode.items()]
    tm = Table(mode_rows, colWidths=[200, 280])
    tm.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elements.append(tm)
    elements.append(Spacer(1, 8))

    # Biaya Umum
    elements.append(Paragraph("Biaya Umum", heading_style))
    umum_rows = [["Item", "Rp"]] + [[k, format_rp(v)] for k, v in biaya_umum.items()]
    tu = Table(umum_rows, colWidths=[200, 280])
    tu.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elements.append(tu)
    elements.append(Spacer(1, 10))

    # Profit scenario table
    elements.append(Paragraph("Skenario Profit (0% - 50%)", heading_style))
    data_profit = [profit_df.columns.tolist()] + profit_df.values.tolist()
    # convert numeric strings to formatted Rp in table rows
    # profit_df already formatted as strings; we keep them
    tp = Table(data_profit, colWidths=[60, 110, 120, 100, 120])
    tp.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elements.append(tp)
    elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

pdf_buffer = generate_pdf_report()
st.download_button("📥 Download Laporan PDF (RAPI)", data=pdf_buffer,
                   file_name=f"Freight_Report_{pol or 'POL'}_{pod or 'POD'}.pdf",
                   mime="application/pdf")

# End of app
