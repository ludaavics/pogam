import logging
import sys
from os import getenv, makedirs, path
from typing import Dict, Optional

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


# misc app-wide config
SOURCES = ["leboncoin", "seloger"]


def create_app(ui: str = "web", config: Optional[Dict[str, str]] = None) -> Flask:
    """
    Create a flask app.

    Args:
        ui: user interface of the app. One of {'web', 'cli'}.
        config: app configuration parameters.

    Returns:
        initialized Flask app.
    """
    app = Flask(__name__)
    if config is None:
        config = {}

    # configure logging
    app.logger.setLevel(logging.DEBUG)
    datefmt = "%d%b%Y %H:%M:%S"
    fmt = {
        "web": "%(asctime)s - %(name)s.%(lineno)s - %(levelname)s - %(message)s",
        "cli": "%(asctime)s - %(message)s",
    }[ui]
    formatter = logging.Formatter(fmt, datefmt)
    [h.setFormatter(formatter) for h in app.logger.handlers]

    gunicorn_handler = logging.getLogger("gunicorn.error").handlers
    flask_handler = logging.StreamHandler(sys.stdout)
    flask_handler.setLevel(logging.DEBUG)
    flask_handler.setFormatter(formatter)
    app.logger.handlers = gunicorn_handler
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
    cfg.update(config)
    app.config.update(cfg)

    db.init_app(app)
    from pogam import models  # noqa

    if "sqlite" in db_url:
        with app.app_context():
            db.create_all()

    return app


version: Dict[str, str] = {}
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "__version__.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]
__release__ = version["__release__"]
