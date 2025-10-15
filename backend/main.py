from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests, base64, json
from datetime import datetime, timedelta

app = FastAPI()

# ==== CONFIG MIDTRANS ====
MIDTRANS_SERVER_KEY = "Mid-server-IJD2MBz-xxxxxx12345abcde"
MIDTRANS_URL = "https://api.sandbox.midtrans.com/v2/charge"

# ==== CORS (biar Streamlit bisa akses backend) ====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Helper buat bikin header Midtrans ====
def make_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode((MIDTRANS_SERVER_KEY + ":").encode()).decode()
    }

# ==== Route utama buat bikin transaksi ====
@app.post("/create_transaction")
def create_transaction(data: dict):
    """
    data = {
        "email": "user@email.com",
        "package": "7",  # durasi hari (7, 30, 90)
        "amount": 50000  # nominal
    }
    """

    try:
        order_id = f"{data['email'].replace('@', '_').replace('.', '_')}_{int(datetime.now().timestamp())}"

        payload = {
            "payment_type": "bank_transfer",
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": data["amount"]
            },
            "bank_transfer": {
                "bank": "bca"
            },
            "customer_details": {
                "email": data["email"]
            }
        }

        headers = make_headers()
        response = requests.post(MIDTRANS_URL, headers=headers, json=payload)
print("Midtrans Response:", response.status_code, response.text)  # debug

if response.text.strip() == "":
    raise HTTPException(status_code=400, detail="Midtrans tidak mengembalikan respons apa pun")

if response.status_code not in [200, 201]:
    raise HTTPException(status_code=response.status_code, detail=response.text)

        result = response.json()
        return {
            "order_id": order_id,
            "va_number": result["va_numbers"][0]["va_number"],
            "bank": result["va_numbers"][0]["bank"],
            "payment_url": result.get("redirect_url", ""),
            "status": "PENDING"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==== Tes koneksi ====
@app.get("/")
def home():
    return {"status": "Backend aktif", "time": datetime.now().isoformat()}
