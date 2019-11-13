import logging
import sys
from os import getenv, makedirs, path
from typing import Dict

from flask import Flask
from flask_sqlalchemy import SQLAlchemy  # type: ignore
from sqlalchemy import MetaData  # type: ignore

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# naming conventions
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": ("fk_%(table_name)s_%(column_0_name)s_" "%(referred_table_name)s"),
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


def create_app(cfg=None):

    app = Flask(__name__)

    # configure logging
    app.logger.handlers = logging.getLogger("gunicorn.error").handlers
    app.logger.setLevel(logging.DEBUG)

    fmt = "%(asctime)s - %(name)s.%(lineno)s - %(levelname)s - %(message)s"
    datefmt = "%d%b%Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)
    [h.setFormatter(formatter) for h in app.logger.handlers]

    if not app.logger.handlers:
        flask_handler = logging.StreamHandler(sys.stdout)
        flask_handler.setLevel(logging.DEBUG)
        flask_handler.setFormatter(formatter)
        app.logger.addHandler(flask_handler)

    # configure app instance
    db_url = getenv("POGAM_DATABASE_URL", None)
    if db_url is None:
        folder = path.expanduser("~/.pogam/")
        makedirs(folder, exist_ok=True)
        db_url = f"sqlite:///{path.join(folder, 'db.sqlite')}"
    cfg = {
        "SESSION_SECRET_KEY": getenv("SESSION_SECRET_KEY", "not so secret key"),
        "SQLALCHEMY_DATABASE_URI": db_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    }
    app.config.update(cfg)

    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app


version: Dict[str, str] = {}
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "__version__.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]
__release__ = version["__release__"]
