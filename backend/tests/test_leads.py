
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from main import app
from database import get_db
from models import Lead
import os

@pytest.fixture
def test_setup():

    fake_db = Mock(spec=Session)

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            client.headers.update({
                "X-Internal-API-Key": os.environ["INTERNAL_API_KEY"]
            })
            yield client, fake_db
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_existing_lead(test_setup):

    client, fake_db = test_setup

    fake_db.get.return_value = SimpleNamespace(
        id=2,
        name="Ali Ahmed",
        service="ac_repair",
        status="new",
        created_at=datetime.now(timezone.utc)
    )

    response = client.get("/leads/2")

    assert response.status_code == 200
    assert response.json()["name"] == "Ali Ahmed"

    fake_db.get.assert_called_once_with(Lead, 2)


def test_get_missing_lead(test_setup):

    client, fake_db = test_setup

    fake_db.get.return_value = None

    response = client.get("/leads/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_database_unavailable(test_setup):

    client, fake_db = test_setup

    fake_db.get.side_effect = OperationalError(
        "SELECT lead",
        {},
        Exception("Simulated connection failure")
    )

    response = client.get("/leads/1")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Database temporarily unavailable"
    )

    fake_db.rollback.assert_called_once()


def test_missing_api_key_is_rejected(test_setup):

    client, fake_db = test_setup

    # Remove the valid key added by our fixture
    client.headers.pop("X-Internal-API-Key", None)

    response = client.get("/leads/1")

    assert response.status_code == 401

    # Database must not be queried
    fake_db.get.assert_not_called()


def test_invalid_api_key_is_rejected(test_setup):

    client, fake_db = test_setup

    client.headers["X-Internal-API-Key"] = "wrong-key"

    response = client.get("/leads/1")

    assert response.status_code == 401

    fake_db.get.assert_not_called()
