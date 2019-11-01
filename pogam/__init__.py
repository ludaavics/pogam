from os import path

version = {}
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "__version__.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]
__release__ = version["__release__"]
