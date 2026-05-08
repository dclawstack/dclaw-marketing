from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    ALL models MUST inherit from this class.
    NEVER use sqlalchemy.orm.declarative_base() separately.
    """
    pass
