
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Text,
    func,
    text,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class Lead(Base):

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    phone: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    service: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'new'")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
