# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests, base64

app = FastAPI()

# 🔑 Ganti dengan Midtrans Server Key sandbox kamu
MIDTRANS_SERVER_KEY = "Mid-server-IJD2MBz-xxxxxx12345abcde"
MIDTRANS_URL = "https://api.sandbox.midtrans.com/v2/charge"

# 🔓 Ijinkan diakses dari Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def make_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode((MIDTRANS_SERVER_KEY + ":").encode()).decode()
    }

@app.get("/")
def home():
    return {"status": "Backend aktif"}

@app.post("/create_transaction")
def create_transaction(data: dict):
    try:
        payload = {
            "payment_type": "bank_transfer",
            "transaction_details": {
                "order_id": "order_" + data["email"].replace("@", "_"),
                "gross_amount": data["amount"]
            },
            "bank_transfer": {"bank": "bca"},
            "customer_details": {"email": data["email"]}
        }

        response = requests.post(MIDTRANS_URL, headers=make_headers(), json=payload)
        print("Midtrans Response:", response.status_code, response.text)

        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
