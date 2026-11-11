
import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from models import Base, Lead


# Load project environment configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# Explicitly connect to TEST database
test_database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    database="serviceflow_test",
)

test_engine = create_engine(test_database_url)


def test_rollback_removes_uncommitted_lead():

    # Create tables in test database only
    Base.metadata.create_all(test_engine)

    # First database session
    with Session(test_engine) as session:

        lead = Lead(
            name="Test Customer",
            phone="03000000000",
            service="ac_repair",
            message="This is a database integration test"
        )

        session.add(lead)
        session.flush()

        lead_id = lead.id

        # Confirm INSERT is visible in this transaction
        saved_name = session.scalar(
            select(Lead.name).where(Lead.id == lead_id)
        )

        assert saved_name == "Test Customer"

        # Cancel uncommitted changes
        session.rollback()

    # Completely new database session
    with Session(test_engine) as verification_session:

        saved_lead = verification_session.get(
            Lead,
            lead_id
        )

        assert saved_lead is None
