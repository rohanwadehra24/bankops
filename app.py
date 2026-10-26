import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
load_dotenv()
DATABASE_URL=os.getenv("DATABASE_URL")

def get_connection():
    return psycopg.connect(DATABASE_URL)



app = FastAPI(title="BankOps")
transactions = {}


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    currency: str
    transaction_type: str

def evaluate_transaction(amount: float) -> str:
    if amount >= 100000:
        return "REVIEW"
    return "CLEAR"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"application": "BankOps", "version": "1.1.0"}


@app.post("/transactions")
def create_transaction(transaction: Transaction):
    monitoring_outcome = evaluate_transaction(transaction.amount)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (
                    transaction_id,
                    account_id,
                    amount,
                    currency,
                    transaction_type,
                    processing_status,
                    monitoring_outcome
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    transaction.transaction_id,
                    transaction.account_id,
                    transaction.amount,
                    transaction.currency,
                    transaction.transaction_type,
                    "PROCESSED",
                    monitoring_outcome,
                ),
            )

    return {
        "status": "accepted",
        "monitoring_outcome": monitoring_outcome,
        "transaction": transaction
    }

@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transaction_id,
                    account_id,
                    amount,
                    currency,
                    transaction_type,
                     processing_status,
                     monitoring_outcome
                FROM transactions
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found"
        )

    return {
        "status": "found",
        "transaction": {
            "transaction_id": row[0],
            "account_id": row[1],
            "amount": float(row[2]),
            "currency": row[3],
            "transaction_type": row[4],
            "processing_status": row[5],
            "monitoring_outcome": row[6],
        }
    }
