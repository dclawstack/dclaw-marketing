from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass, kw_only=True):
    """Base class for all SQLAlchemy models.

    ALL models MUST inherit from this class.
    NEVER use sqlalchemy.orm.declarative_base() separately.
    """
    pass
