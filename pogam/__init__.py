from os import makedirs, path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def create_session(db_url: str = None):

    from .models import (  # noqa
        Property,
        Listing,
        PropertyType,
        TransactionType,
        HeatingType,
        KitchenType,
        City,
        Neighborhood,
    )

    if db_url is None:
        folder = path.expanduser("~/.pogam/")
        makedirs(folder, exist_ok=True)
        db_url = f"sqlite:///{path.join(folder, 'db.sqlite')}"

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    return session


version = {}
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "__version__.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]
__release__ = version["__release__"]
