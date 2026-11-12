
import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from models import Base, Lead
from fastapi.testclient import TestClient
from sqlalchemy import text
from main import app
from database import get_db

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


def test_api_post_get_with_savepoint():

    # Safety: never run against the development database
    assert test_engine.url.database == "serviceflow_test"

    Base.metadata.create_all(test_engine)

    # Real PostgreSQL connection
    with test_engine.connect() as connection:

        # Start outer transaction
        outer_transaction = connection.begin()

        # Override FastAPI's database dependency
        def override_get_db():
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False
            ) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:

                # 1. Create a real lead through FastAPI
                response = client.post(
                    "/leads",
                    json={
                        "name": "Integration Test Customer",
                        "phone": "03000000000",
                        "service": "plumbing",
                        "message": "My kitchen pipe is leaking badly"
                    },
                    headers={
                        "Idempotency-Key": "integration-post-get-001"
                    }
                )

                assert response.status_code == 201, response.text

                created = response.json()
                lead_id = created["id"]

                assert created["name"] == "Integration Test Customer"
                assert created["status"] == "new"

                # 2. Read the same lead through FastAPI
                get_response = client.get(f"/leads/{lead_id}")

                assert get_response.status_code == 200
                assert get_response.json()["id"] == lead_id

                # 3. Verify the row through SQL
                count = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM leads "
                        "WHERE id = :lead_id"
                    ),
                    {"lead_id": lead_id}
                ).scalar_one()

                assert count == 1

        finally:
            # Restore normal FastAPI dependency behavior
            app.dependency_overrides.pop(get_db, None)

            # Undo all test data changes
            outer_transaction.rollback()

    # 4. Check from a new database connection
    with test_engine.connect() as verification:

        remaining = verification.execute(
            text(
                "SELECT COUNT(*) FROM leads "
                "WHERE id = :lead_id"
            ),
            {"lead_id": lead_id}
        ).scalar_one()

        assert remaining == 0



def test_duplicate_request_creates_only_one_lead():

    assert test_engine.url.database == "serviceflow_test"

    Base.metadata.create_all(test_engine)

    with test_engine.connect() as connection:

        outer_transaction = connection.begin()

        def override_get_db():
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False
            ) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:

                payload = {
                    "name": "Duplicate Test Customer",
                    "phone": "03001112222",
                    "service": "plumbing",
                    "message": "My kitchen pipe is leaking."
                }

                headers = {
                    "Idempotency-Key": "test-request-001"
                }

                # First request
                first = client.post(
                    "/leads",
                    json=payload,
                    headers=headers
                )

                # Retry the exact same request
                second = client.post(
                    "/leads",
                    json=payload,
                    headers=headers
                )

                changed_payload = {
                        **payload,
    "service": "electrical"
                    }

                conflict = client.post(
    "/leads",
    json=changed_payload,
    headers=headers
)

                assert conflict.status_code == 409

                assert first.status_code == 201
                assert second.status_code == 200

                # Both should refer to the SAME lead
                assert first.json()["id"] == second.json()["id"]

        finally:
            app.dependency_overrides.pop(get_db, None)
            outer_transaction.rollback()
