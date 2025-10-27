# app.py
import streamlit as st
from datetime import datetime, date, time, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="⚓ Voyage Report – Demurrage/Detention", layout="wide")
st.title("⚓ Voyage Report – Detention / Demurrage Calculator")

# ---------------------------
# Helpers
# ---------------------------
def default_time():
    return time(8, 0)

def format_rp(x):
    try:
        return "Rp {:,}".format(int(round(x))).replace(",", ".")
    except:
        return f"Rp {x}"

def safe_datetime(d: date, t: time):
    return datetime.combine(d, t)

def duration_hours_between(first_dt: datetime, last_dt: datetime) -> float:
    """Return hours between two datetimes; if last < first returns 0."""
    diff = (last_dt - first_dt).total_seconds() / 3600.0
    return max(0.0, diff)

def build_pdf(context: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", alignment=1, fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="SubHeader", fontSize=11, spaceBefore=8, spaceAfter=6, textColor=colors.darkblue))

    elems = []
    elems.append(Paragraph("⚓ VOYAGE REPORT – DETENTION / DEMURRAGE", styles["CenterTitle"]))
    elems.append(Spacer(1, 6))

    # Info
    elems.append(Paragraph("<b>Informasi Umum</b>", styles["SubHeader"]))
    info = [
        ["Tug Boat", context.get("tugboat","")],
        ["Barge", context.get("barge","")],
        ["Port of Loading (POL)", context.get("pol","")],
        ["Port of Discharge (POD)", context.get("pod","")],
        ["Shipper", context.get("shipper","")],
        ["Laycan", context.get("laycan","")],
        ["Free Time (Prorata)", f"{context.get('prorata',0):.2f} Hari"],
        ["Rate Demurrage", f"{format_rp(context.get('rate_per_day',0))} / Hari"],
    ]
    t_info = Table(info, colWidths=[160, 340])
    t_info.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))
    elems.append(t_info)
    elems.append(Spacer(1, 10))

    # Voyage POL
    elems.append(Paragraph("<b>Voyage Events – POL</b>", styles["SubHeader"]))
    pol_rows = [["No", "Date", "Time", "Status"]]
    for i, r in enumerate(context.get("pol_rows", []), start=1):
        pol_rows.append([
            str(i),
            r["Date"].strftime("%d %b %Y"),
            r["Time"].strftime("%H:%M"),
            r.get("Status","")
        ])
    t_pol = Table(pol_rows, colWidths=[30, 100, 60, 310])
    t_pol.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(t_pol)
    elems.append(Spacer(1, 8))

    # Voyage POD
    elems.append(Paragraph("<b>Voyage Events – POD</b>", styles["SubHeader"]))
    pod_rows = [["No", "Date", "Time", "Status"]]
    for i, r in enumerate(context.get("pod_rows", []), start=1):
        pod_rows.append([
            str(i),
            r["Date"].strftime("%d %b %Y"),
            r["Time"].strftime("%H:%M"),
            r.get("Status","")
        ])
    t_pod = Table(pod_rows, colWidths=[30, 100, 60, 310])
    t_pod.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    elems.append(t_pod)
    elems.append(Spacer(1, 10))

    # Summary
    elems.append(Paragraph("<b>Perhitungan Akhir</b>", styles["SubHeader"]))
    summary = [
        ["Durasi POL", f"{context['pol_hours']:.2f} Jam ({context['pol_hours']/24:.2f} Hari)"],
        ["Durasi POD", f"{context['pod_hours']:.2f} Jam ({context['pod_hours']/24:.2f} Hari)"],
        ["Total Durasi (POL + POD)", f"{context['total_hours']:.2f} Jam ({context['total_days']:.2f} Hari)"],
        ["Free Time (Prorata)", f"{context['prorata']:.2f} Hari"],
        ["Detention / Demurrage Days", f"{context['detention_days']:.2f} Hari"],
        ["Total Biaya Demurrage", f"{format_rp(context['total_cost'])}"],
    ]
    t_sum = Table(summary, colWidths=[220, 280])
    t_sum.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,5), (-1,5), colors.whitesmoke),
        ("TEXTCOLOR", (0,5), (-1,5), colors.red),
    ]))
    elems.append(t_sum)

    doc.build(elems)
    buf.seek(0)
    return buf.read()

# ---------------------------
# Session init for rows
# ---------------------------
if "pol_rows" not in st.session_state:
    st.session_state.pol_rows = []
if "pod_rows" not in st.session_state:
    st.session_state.pod_rows = []

# ---------------------------
# Mode Input header
# ---------------------------
st.header("📥 Input Data Utama")
col1, col2 = st.columns(2)
with col1:
    tugboat = st.text_input("Tug Boat")
    pol = st.text_input("Port of Loading (POL)")
    shipper = st.text_input("Shipper")
with col2:
    barge = st.text_input("Barge")
    pod = st.text_input("Port of Discharge (POD)")
    laycan = st.text_input("Laycan (contoh: 20–22 Oct 2025)")

col3, col4 = st.columns(2)
with col3:
    prorata = st.number_input("Prorata (Free Time – Hari)", min_value=0.0, step=0.5, value=0.0)
with col4:
    rate_per_day = st.number_input("Rate Demurrage (Rp/Hari)", min_value=0.0, step=100000.0, value=0.0, format="%.0f")

st.markdown("---")

# ---------------------------
# POL voyage events (single time input per row)
# ---------------------------
st.subheader("1️⃣ Port of Loading (POL) — Voyage Events")
pol_col_left, pol_col_right = st.columns([3,1])
with pol_col_left:
    st.write("Isi event POL: tanggal + jam + keterangan. Sistem akan menghitung durasi dari event pertama → terakhir.")
with pol_col_right:
    def add_pol():
        st.session_state.pol_rows.append({"Date": date.today(), "Time": default_time(), "Status": ""})
    st.button("➕ Tambah Baris POL", on_click=add_pol)

# render rows safely and rebuild list
new_pol_rows = []
for i, row in enumerate(st.session_state.pol_rows):
    cols = st.columns([0.5, 2, 1, 3, 0.6])
    cols[0].markdown(f"**{i+1}**")
    d_key = f"pol_date_{i}"
    t_key = f"pol_time_{i}"
    s_key = f"pol_status_{i}"

    # initialize session defaults if not set
    if d_key not in st.session_state:
        st.session_state[d_key] = row["Date"]
    if t_key not in st.session_state:
        st.session_state[t_key] = row["Time"]
    if s_key not in st.session_state:
        st.session_state[s_key] = row.get("Status","")

    # widgets
    st_date = cols[1].date_input("", value=st.session_state[d_key], key=d_key)
    st_time = cols[2].time_input("", value=st.session_state[t_key], key=t_key, step=60)
    st_status = cols[3].text_input("", value=st.session_state[s_key], key=s_key)
    remove = cols[4].button("❌", key=f"pol_remove_{i}")

    if not remove:
        new_pol_rows.append({"Date": st_date, "Time": st_time, "Status": st_status})
    else:
        # remove: also delete session keys to avoid stale keys
        for k in (d_key, t_key, s_key, f"pol_remove_{i}"):
            if k in st.session_state:
                try:
                    del st.session_state[k]
                except Exception:
                    pass

st.session_state.pol_rows = new_pol_rows

st.markdown("---")

# ---------------------------
# POD voyage events
# ---------------------------
st.subheader("2️⃣ Port of Discharge (POD) — Voyage Events")
pod_col_left, pod_col_right = st.columns([3,1])
with pod_col_left:
    st.write("Isi event POD: tanggal + jam + keterangan. Sistem akan menghitung durasi dari event pertama → terakhir.")
with pod_col_right:
    def add_pod():
        st.session_state.pod_rows.append({"Date": date.today(), "Time": default_time(), "Status": ""})
    st.button("➕ Tambah Baris POD", on_click=add_pod)

new_pod_rows = []
for i, row in enumerate(st.session_state.pod_rows):
    cols = st.columns([0.5, 2, 1, 3, 0.6])
    cols[0].markdown(f"**{i+1}**")
    d_key = f"pod_date_{i}"
    t_key = f"pod_time_{i}"
    s_key = f"pod_status_{i}"

    if d_key not in st.session_state:
        st.session_state[d_key] = row["Date"]
    if t_key not in st.session_state:
        st.session_state[t_key] = row["Time"]
    if s_key not in st.session_state:
        st.session_state[s_key] = row.get("Status","")

    st_date = cols[1].date_input("", value=st.session_state[d_key], key=d_key)
    st_time = cols[2].time_input("", value=st.session_state[t_key], key=t_key, step=60)
    st_status = cols[3].text_input("", value=st.session_state[s_key], key=s_key)
    remove = cols[4].button("❌", key=f"pod_remove_{i}")

    if not remove:
        new_pod_rows.append({"Date": st_date, "Time": st_time, "Status": st_status})
    else:
        for k in (d_key, t_key, s_key, f"pod_remove_{i}"):
            if k in st.session_state:
                try:
                    del st.session_state[k]
                except Exception:
                    pass

st.session_state.pod_rows = new_pod_rows

st.markdown("---")

# ---------------------------
# Calculation & display
# ---------------------------
st.subheader("📊 Hasil Perhitungan")

# compute durations: if no rows -> 0
def compute_first_last_hours(rows):
    if not rows:
        return 0.0, None, None  # hours, first_dt, last_dt
    # build datetimes
    dts = []
    for r in rows:
        try:
            dt = safe_datetime(r["Date"], r["Time"])
            dts.append(dt)
        except Exception:
            continue
    if not dts:
        return 0.0, None, None
    dts_sorted = sorted(dts)
    first_dt = dts_sorted[0]
    last_dt = dts_sorted[-1]
    hours = duration_hours_between(first_dt, last_dt)
    return hours, first_dt, last_dt

pol_hours, pol_first, pol_last = compute_first_last_hours(st.session_state.pol_rows)
pod_hours, pod_first, pod_last = compute_first_last_hours(st.session_state.pod_rows)
total_hours = pol_hours + pod_hours
total_days = total_hours / 24.0
detention_days = max(0.0, total_days - prorata)
total_cost = detention_days * rate_per_day

# Display nicely
if pol_first and pol_last:
    st.write(f"• POL: {pol_first.strftime('%d %b %Y %H:%M')} → {pol_last.strftime('%d %b %Y %H:%M')} = **{pol_hours:.2f} jam ({pol_hours/24:.2f} hari)**")
else:
    st.write("• POL: belum ada event lengkap (masukkan minimal 1 event).")

if pod_first and pod_last:
    st.write(f"• POD: {pod_first.strftime('%d %b %Y %H:%M')} → {pod_last.strftime('%d %b %Y %H:%M')} = **{pod_hours:.2f} jam ({pod_hours/24:.2f} hari)**")
else:
    st.write("• POD: belum ada event lengkap (masukkan minimal 1 event).")

st.markdown("---")
st.write(f"**Total (POL + POD):** {total_hours:.2f} jam ({total_days:.2f} hari)")
st.write(f"**Free Time (Prorata):** {prorata:.2f} hari")
st.write(f"**Detention / Demurrage Days:** {detention_days:.2f} hari")
st.write(f"**Total Biaya Demurrage:** {format_rp(total_cost)}")

st.markdown("---")

# ---------------------------
# PDF export
# ---------------------------
if st.button("📄 Download PDF Report", use_container_width=True):
    context = {
        "tugboat": tugboat,
        "barge": barge,
        "pol": pol,
        "pod": pod,
        "shipper": shipper,
        "laycan": laycan,
        "prorata": prorata,
        "rate_per_day": rate_per_day,
        "pol_rows": st.session_state.pol_rows,
        "pod_rows": st.session_state.pod_rows,
        "pol_hours": pol_hours,
        "pod_hours": pod_hours,
        "total_hours": total_hours,
        "total_days": total_days,
        "detention_days": detention_days,
        "total_cost": total_cost,
    }
    pdf_bytes = build_pdf(context)
    st.download_button(
        label="💾 Simpan PDF",
        data=pdf_bytes,
        file_name=f"Voyage_Report_{tugboat or 'vessel'}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
