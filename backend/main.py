
import logging
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Lead

app = FastAPI(title="ServiceFlow AI")

logger = logging.getLogger(__name__)

# Incoming API request
class LeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=25)
    service: Literal["ac_repair", "plumbing", "electrical"]
    message: str = Field(min_length=10, max_length=2000)

# Outgoing API response
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

@app.post(
    "/leads",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED
)
def create_lead(
    lead: LeadRequest,
    db: Session = Depends(get_db)
):

    new_lead = Lead(
        name=lead.name,
        phone=lead.phone,
        service=lead.service,
        message=lead.message
    )

    try:
        db.add(new_lead)

        db.flush()

        db.refresh(new_lead)

        db.commit()

    except OperationalError:
        db.rollback()
        logger.exception("Database connection failed")

        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable"
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to save lead")

        raise HTTPException(
            status_code=500,
            detail="Could not create lead"
        )

    return new_lead



@app.get(
    "/leads/{lead_id}",
    response_model=LeadResponse
)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db)
):
    try:
        lead = db.get(Lead, lead_id)

    except OperationalError:
        db.rollback()
        logger.exception("Database unavailable while reading lead")

        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable"
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to retrieve lead")

        raise HTTPException(
            status_code=500,
            detail="Could not retrieve lead"
        )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    return lead