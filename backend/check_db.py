
from sqlalchemy import text
from database import engine


with engine.connect() as connection:

    result = connection.execute(
        text(
            "SELECT COUNT(*) FROM leads"
        )
    )
    total_leads = result.scalar_one()
    print("Total leads:", total_leads)