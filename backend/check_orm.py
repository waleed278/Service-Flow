
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from models import Lead


with Session(engine) as session:

    statement = select(Lead).order_by(Lead.id).limit(5)

    leads = session.scalars(statement).all()

    print("Leads found:", len(leads))

    for lead in leads:
        print("----------------")
        print("ID:", lead.id)
        print("Name:", lead.name)
        print("Service:", lead.service)
        print("Status:", lead.status)
