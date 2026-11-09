
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

app = FastAPI(title="ServiceFlow AI")


class LeadRequest(BaseModel):
    name: str = Field(min_length=2)
    phone: str = Field(min_length=7)
    service: Literal["ac_repair", "plumbing", "electrical"]
    message: str = Field(min_length=10)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/leads")
def receive_lead(lead: LeadRequest):
    return {
        "valid": True,
        "stored": False,
        "customer": lead.name,
        "service": lead.service,
        "message": "Request validated successfully"
    }
