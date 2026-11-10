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
