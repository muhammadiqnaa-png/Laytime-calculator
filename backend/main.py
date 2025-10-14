# backend/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests, base64, os

app = FastAPI()

# 🔑 Ambil Server Key dari Streamlit Secrets (kalau lokal fallback ke variabel)
MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY", "Mid-server-IJD2MBz-4teBow5h67KiRyEJ")
MIDTRANS_URL = "https://api.sandbox.midtrans.com/v2/charge"

# 🔓 Ijinkan diakses dari Streamlit Cloud / localhost
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
    return {"status": "✅ Backend aktif & siap konek ke Midtrans"}

@app.post("/create_transaction")
async def create_transaction(request: Request):
    try:
        data = await request.json()
        if "email" not in data or "amount" not in data:
            raise HTTPException(status_code=400, detail="Data tidak lengkap (email / amount)")

        payload = {
            "payment_type": "bank_transfer",
            "transaction_details": {
                "order_id": "order_" + data["email"].replace("@", "_"),
                "gross_amount": int(data["amount"])
            },
            "bank_transfer": {"bank": "bca"},
            "customer_details": {"email": data["email"]}
        }

        response = requests.post(MIDTRANS_URL, headers=make_headers(), json=payload)

        if response.status_code not in [200, 201]:
            print("❌ Midtrans error:", response.status_code, response.text)
            raise HTTPException(status_code=response.status_code, detail=response.text)

        print("✅ Midtrans success:", response.json())
        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
