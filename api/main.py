from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
import os

app = FastAPI(title="ReValix Read-Only API")

# ================= CORS (allow Streamlit Cloud) =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict later to your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= Database Config =================
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

engine = create_engine(
    f"mssql+pymssql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
)

# ================= Routes =================
@app.get("/")
def home():
    return {"message": "ReValix Read-Only API is running."}

@app.get("/property/{acct}")
def get_property(acct: str):
    """Fetch property details for given ACCT from all relevant tables"""
    tables = [
        "Real_acct_owner_real_acct",
        "Real_acct_owner_Owners",
        "Real_acct_owner_Deeds",
        "Real_acct_owner_permits",
        "Real_acct_ownership_historyownership_history"
    ]
    results = {}
    try:
        with engine.connect() as conn:
            for t in tables:
                query = text(f"SELECT * FROM dbo.{t} WHERE acct = :acct")
                df = pd.read_sql_query(query, conn, params={"acct": acct})
                results[t] = df.to_dict(orient="records")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
