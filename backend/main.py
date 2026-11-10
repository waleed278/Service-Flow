import logging
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, Depends,HTTPException, status
from pydantic import BaseModel,ConfigDict, Field
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Lead

app = FastAPI(title="Service Flow")

logger = logging.getLogger(__name__)

class LeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=25)
    service: Literal["ac_repair", "plumbing", "electrical"]
    message: str = Field(min_length=10, max_length=2000)

class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    service: str
    status: str
    created_at: datetime

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/leads",response_model=LeadResponse,status_code=status.HTTP_201_CREATED)
def create_lead(lead:LeadRequest,db: Session = Depends(get_db)):
    new_lead = Lead(
        name = lead.name,
        phone = lead.phone,
        service = lead.service,
        message = lead.message
    )

    try:
        db.add(new_lead)
        db.refresh(new_lead)
        db.commit()
    except OperationalError:
        db.rollback()
        logger.exception("Database Connection Failed")

        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavaiable"
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to save Lead")

        raise HTTPException(
            status_code=500,
            detail="Could not create lead"
        )

    return new_lead


