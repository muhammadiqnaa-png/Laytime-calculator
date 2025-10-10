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
# Database Setup (Auto Update)
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Buat tabel kapal kalau belum ada
    c.execute("""
        CREATE TABLE IF NOT EXISTS kapal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT
        )
    """)

    # Tambah kolom baru jika belum ada
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(kapal)")]
    new_cols = {
        "speed_isi": "REAL",
        "speed_kosong": "REAL",
        "consumption_isi": "REAL",
        "consumption_kosong": "REAL",
        "consumption_port": "REAL",
        "daily_cost": "REAL",
        "total_cargo": "REAL"
    }
    for col, typ in new_cols.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE kapal ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def load_kapal():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM kapal", conn)
    conn.close()
    return df


def save_kapal(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if data.get("id"):
        c.execute("""
            UPDATE kapal SET nama=?, speed_isi=?, speed_kosong=?, consumption_isi=?, 
            consumption_kosong=?, consumption_port=?, daily_cost=?, total_cargo=? WHERE id=?
        """, (
            data["nama"], data["speed_isi"], data["speed_kosong"], data["consumption_isi"],
            data["consumption_kosong"], data["consumption_port"], data["daily_cost"],
            data["total_cargo"], data["id"]
        ))
    else:
        c.execute("""
            INSERT INTO kapal (nama, speed_isi, speed_kosong, consumption_isi, consumption_kosong, 
            consumption_port, daily_cost, total_cargo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["nama"], data["speed_isi"], data["speed_kosong"], data["consumption_isi"],
            data["consumption_kosong"], data["consumption_port"], data["daily_cost"], data["total_cargo"]
        ))
    conn.commit()
    conn.close()


# ==============================
# Inisialisasi DB
# ==============================
init_db()
kapal_df = load_kapal()

st.title("🚢 Freight Calculator Demo (Final)")

# ==============================
# Sidebar - Mode & Parameter
# ==============================
with st.sidebar.expander("⚙️ Mode & Pilihan Kapal", expanded=True):
    mode = st.radio("Pilih Mode:", ["Owner", "Charter Hire"])
    kapal_list = ["-- Kapal Baru --"] + kapal_df["nama"].tolist()
    selected_kapal = st.selectbox("Pilih Kapal:", kapal_list)

    if selected_kapal != "-- Kapal Baru --":
        kapal_data = kapal_df[kapal_df["nama"] == selected_kapal].iloc[0].to_dict()
    else:
        kapal_data = None

with st.sidebar.expander("📦 Data Kapal"):
    nama_kapal_input = st.text_input("Nama Kapal", value=kapal_data["nama"] if kapal_data else "")
    total_cargo = st.number_input("Total Cargo (MT)", value=float(kapal_data["total_cargo"]) if kapal_data and "total_cargo" in kapal_data else 0.0)
    speed_isi = st.number_input("Speed Isi (knot)", value=float(kapal_data["speed_isi"]) if kapal_data and "speed_isi" in kapal_data else 0.0)
    speed_kosong = st.number_input("Speed Kosong (knot)", value=float(kapal_data["speed_kosong"]) if kapal_data and "speed_kosong" in kapal_data else 0.0)
    consumption_isi = st.number_input("Consumption Laden (liter/jam)", value=float(kapal_data["consumption_isi"]) if kapal_data and "consumption_isi" in kapal_data else 0.0)
    consumption_kosong = st.number_input("Consumption Ballast (liter/jam)", value=float(kapal_data["consumption_kosong"]) if kapal_data and "consumption_kosong" in kapal_data else 0.0)
    consumption_port = st.number_input("Consumption Port (liter/hari)", value=float(kapal_data["consumption_port"]) if kapal_data and "consumption_port" in kapal_data else 0.0)
    daily_cost = st.number_input("Daily Cost (Rp/hari)", value=float(kapal_data["daily_cost"]) if kapal_data and "daily_cost" in kapal_data else 0.0)

with st.sidebar.expander("⚓ Parameter Voyage"):
    jarak_laden = st.number_input("Jarak Laden (mil laut)", value=0.0)
    jarak_ballast = st.number_input("Jarak Ballast (mil laut)", value=0.0)
    port_days = st.number_input("Port Days (hari)", value=0.0)
    harga_bbm = st.number_input("Harga BBM (Rp/liter)", value=0.0)

with st.sidebar.expander("💾 Simpan Data Kapal"):
    if st.button("💾 Simpan/Update Kapal"):
        save_kapal({
            "id": kapal_data["id"] if kapal_data else None,
            "nama": nama_kapal_input,
            "speed_isi": speed_isi,
            "speed_kosong": speed_kosong,
            "consumption_isi": consumption_isi,
            "consumption_kosong": consumption_kosong,
            "consumption_port": consumption_port,
            "daily_cost": daily_cost,
            "total_cargo": total_cargo
        })
        st.success("Data kapal berhasil disimpan!")

# ==============================
# Perhitungan
# ==============================
sailing_time = (
    (jarak_laden / speed_isi if speed_isi else 0) +
    (jarak_ballast / speed_kosong if speed_kosong else 0)
)
voyage_days = sailing_time / 24 + port_days

total_consumption = (
    (sailing_time * consumption_isi if consumption_isi else 0) +
    (sailing_time * consumption_kosong if consumption_kosong else 0) +
    (port_days * consumption_port if consumption_port else 0)
)

biaya_bbm = total_consumption * harga_bbm
biaya_harian = voyage_days * daily_cost
total_cost = biaya_bbm + biaya_harian

freight_mt = total_cost / total_cargo if total_cargo else 0

# ==============================
# Output Utama
# ==============================
st.markdown("## 🚀 Hasil Perhitungan")
col1, col2 = st.columns(2)
col1.metric("Sailing Time (jam)", f"{sailing_time:,.2f}")
col2.metric("Voyage Days (hari)", f"{voyage_days:,.2f}")

col3, col4 = st.columns(2)
col3.metric("Total Consumption (L)", f"{total_consumption:,.0f}")
col4.metric("Total Cost (Rp)", f"{total_cost:,.0f}")

st.metric("Freight per MT (Rp/MT)", f"{freight_mt:,.0f}")

# ==============================
# Profit Scenario
# ==============================
st.markdown("### 💰 Profit Scenario")
profit_df = pd.DataFrame({
    "Profit %": [0, 10, 20, 30, 40, 50],
    "Freight (Rp/MT)": [
        freight_mt * (1 + p / 100) for p in [0, 10, 20, 30, 40, 50]
    ]
})
st.dataframe(profit_df, hide_index=True)

# ==============================
# PDF Report
# ==============================
def generate_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LAPORAN PERHITUNGAN FREIGHT", styles["Heading1"]))
    story.append(Spacer(1, 12))

    data = [
        ["Parameter", "Nilai"],
        ["Jarak Laden (mil)", f"{jarak_laden:,.2f}"],
        ["Jarak Ballast (mil)", f"{jarak_ballast:,.2f}"],
        ["Voyage Days", f"{voyage_days:,.2f}"],
        ["Total Cost (Rp)", f"{total_cost:,.0f}"],
        ["Freight (Rp/MT)", f"{freight_mt:,.0f}"]
    ]
    t = Table(data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8)
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Profit Scenario Table
    story.append(Paragraph("Profit Scenario (0–50%)", styles["Heading2"]))
    data2 = [["Profit %", "Freight (Rp/MT)"]] + profit_df.values.tolist()
    t2 = Table(data2, colWidths=[200, 200])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8)
    ]))
    story.append(t2)

    doc.build(story)
    buffer.seek(0)
    return buffer

pdf_buffer = generate_pdf()
st.download_button("📄 Download PDF", data=pdf_buffer, file_name="Laporan_Freight.pdf", mime="application/pdf")
