# backend/main.py
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import requests
from passlib.hash import bcrypt

# CONFIG: set MIDTRANS_SERVER_KEY and FRONTEND_URL as environment variables
MIDTRANS_SERVER_KEY = os.getenv("Mid_server_IJD2MBz_4teBow5h67KiRyEJ")  # e.g. "SB-Mid-server-xxxx..."
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://freight-calculatordemobyiqna.streamlit.app/")
DB_PATH = os.getenv("DB_PATH", "users.db")

app = FastAPI(title="Prabayar Backend for Freight Demo")

# ----- Database init -----
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # users table
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    active_until TEXT
                )""")
    # purchases table
    c.execute("""CREATE TABLE IF NOT EXISTS purchases (
                    order_id TEXT PRIMARY KEY,
                    email TEXT,
                    days INTEGER,
                    amount INTEGER,
                    status TEXT,
                    created_at TEXT
                )""")
    conn.commit()
    conn.close()

init_db()

# ----- DB helpers -----
def get_user_by_email(email: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id,email,password_hash,active_until FROM users WHERE email=?", (email,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    return {"id": r[0], "email": r[1], "password_hash": r[2], "active_until": r[3]}

def create_user(email: str, password: str):
    ph = bcrypt.hash(password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users(email,password_hash,active_until) VALUES (?,?,?)", (email, ph, None))
    conn.commit()
    conn.close()

def update_active_until(email: str, new_until: datetime):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET active_until=? WHERE email=?", (new_until.strftime("%Y-%m-%d %H:%M:%S"), email))
    conn.commit()
    conn.close()

def save_purchase(order_id: str, email: str, days: int, amount: int, status: str="pending"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO purchases(order_id,email,days,amount,status,created_at)
                 VALUES (?,?,?,?,?,?)""",
              (order_id, email, days, amount, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def set_purchase_status(order_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE purchases SET status=? WHERE order_id=?", (status, order_id))
    conn.commit()
    conn.close()

def get_purchase(order_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT order_id,email,days,amount,status FROM purchases WHERE order_id=?", (order_id,))
    r = c.fetchone()
    conn.close()
    return r

# ----- Auth endpoints -----
@app.post("/register")
async def register(req: Request):
    data = await req.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="User already exists")
    create_user(email, password)
    return {"status": "ok", "msg": "User registered"}

@app.post("/login")
async def login(req: Request):
    data = await req.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"status": "ok", "email": email, "active_until": user["active_until"]}

@app.get("/status/{email}")
async def status(email: str):
    user = get_user_by_email(email)
    if not user:
        return {"email": email, "active": False, "active_until": None}
    if user["active_until"]:
        exp = datetime.strptime(user["active_until"], "%Y-%m-%d %H:%M:%S")
        return {"email": email, "active": datetime.now() < exp, "active_until": user["active_until"]}
    return {"email": email, "active": False, "active_until": None}

# ----- Payment: PACKS & create txn -----
PACKS = {7: 50000, 30: 200000, 90: 500000}

@app.post("/create-transaction")
async def create_transaction(req: Request):
    data = await req.json()
    email = data.get("email")
    days = int(data.get("days", 30))
    if days not in PACKS:
        raise HTTPException(status_code=400, detail="Invalid package days")

    amount = PACKS[days]
    order_id = f"ORDER-{int(datetime.now().timestamp())}-{os.urandom(4).hex()}"

    payload = {
        "external_id": order_id,
        "amount": amount,
        "payer_email": email,
        "description": f"Paket {days} hari - Freight Demo",
        "items": [
            {
                "id": f"pkg_{days}",
                "name": f"Paket {days} Hari",
                "price": amount,
                "quantity": 1
            }
        ],
        "success_redirect_url": f"{FRONTEND_URL}?paid=1&email={email}&order_id={order_id}",
        "failure_redirect_url": f"{FRONTEND_URL}?paid=0&email={email}&order_id={order_id}"
    }

    url = "https://api.sandbox.midtrans.com/v1/payment-links"
    if not MIDTRANS_SERVER_KEY:
        raise HTTPException(status_code=500, detail="MIDTRANS_SERVER_KEY not configured on server")
    auth = (MIDTRANS_SERVER_KEY, "")
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, auth=auth, headers=headers, data=json.dumps(payload))
    if resp.status_code not in (200,201):
        raise HTTPException(status_code=500, detail=f"Midtrans error: {resp.text}")

    data_resp = resp.json()
    payment_url = data_resp.get("url") or data_resp.get("redirect_url") or data_resp.get("checkout_url")
    save_purchase(order_id, email, days, amount, status="pending")
    return {"order_id": order_id, "payment_url": payment_url, "midtrans_resp": data_resp}

# ----- Midtrans webhook -----
@app.post("/midtrans-callback")
async def midtrans_callback(req: Request):
    payload = await req.json()
    # midtrans may deliver different keys. attempt to find external_id/order_id
    status = (payload.get("status") or payload.get("transaction_status") or payload.get("order_status") or "").lower()
    external_id = payload.get("external_id") or payload.get("order_id") or (payload.get("data") or {}).get("external_id")
    if not external_id:
        external_id = payload.get("order", {}).get("external_id") if payload.get("order") else None

    if external_id:
        p = get_purchase(external_id)
        if p:
            # p = (order_id,email,days,amount,status)
            _, email, days, amount, cur_status = p
            if status in ("paid", "settlement", "capture", "success"):
                # extend or set active_until
                user = get_user_by_email(email)
                now = datetime.now()
                if user and user["active_until"]:
                    cur_until = datetime.strptime(user["active_until"], "%Y-%m-%d %H:%M:%S")
                    base = cur_until if cur_until > now else now
                else:
                    base = now
                new_until = base + timedelta(days=int(days))
                update_active_until(email, new_until)
                set_purchase_status(external_id, "settlement")
                return JSONResponse({"status": "ok", "detail": f"user {email} activated until {new_until}"})
            else:
                set_purchase_status(external_id, status or "unknown")
                return JSONResponse({"status": "ok", "detail": f"purchase {external_id} updated to {status}"})
    return JSONResponse({"status": "ignored", "payload_sample": payload})
