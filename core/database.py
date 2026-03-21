from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "sqlite:///finance_os.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Initializes the database by creating all defined tables.

    This function imports the necessary models and creates their corresponding
    tables in the database if they do not already exist. It binds the metadata
    to the SQLAlchemy engine configured for the application.
    """
    from core.models import Asset, Base, Settings

    Base.metadata.create_all(bind=engine)
