
import logging
from datetime import datetime
from typing import Literal


from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Lead

import hashlib
import json
from fastapi import Header,Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
    response: Response,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$"
    ),
    db: Session = Depends(get_db)
):

    # Step 1: Generate a consistent request fingerprint
    payload = lead.model_dump(mode="json")

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    request_hash = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    try:
        # Step 2: Attempt an atomic INSERT
        statement = (
            pg_insert(Lead)
            .values(
                **payload,
                idempotency_key=idempotency_key,
                request_hash=request_hash
            )
            .on_conflict_do_nothing(
                index_elements=[Lead.idempotency_key]
            )
            .returning(Lead.id)
        )

        inserted_id = db.execute(
            statement
        ).scalar_one_or_none()

        # Step 3: New request
        if inserted_id is not None:
            saved_lead = db.get(Lead, inserted_id)

            db.commit()

            return saved_lead

        # Step 4: Key already exists
        existing_lead = db.scalar(
            select(Lead).where(
                Lead.idempotency_key == idempotency_key
            )
        )

        if existing_lead is None:
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Request state could not be resolved"
            )

        # Step 5: Same key but different data
        if existing_lead.request_hash != request_hash:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Idempotency key reused with different data"
            )

        # Step 6: Safe retry
        response.status_code = 200

        db.commit()

        return existing_lead

    except OperationalError:
        db.rollback()
        logger.exception("Database unavailable during lead creation")

        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable"
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to create lead")

        raise HTTPException(
            status_code=500,
            detail="Could not create lead"
        )



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