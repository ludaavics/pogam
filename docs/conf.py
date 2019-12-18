# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../.."))
from pogam import __version__, __release__  # noqa


# -- Project information -----------------------------------------------------

project = "pogam"
copyright = "2019, Ludovic Tiako"
author = "Ludovic Tiako"

# the short X.Y version
version = __version__
# The full version, including alpha/beta/rc tags
release = __release__


# -- General configuration ---------------------------------------------------

# Enable nitpicky mode: all references in the docs must resolve ..
nitpicky = True

# ... and set up known exception
nitpick_ignore = []

for line in open("nitpick-ignore"):
    if line.strip() == "" or line.startswith("#"):
        continue
    dtype, target = line.split(None, 1)
    target = target.strip()
    nitpick_ignore.append((dtype, target))

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "IPython.sphinxext.ipython_console_highlighting",
    "IPython.sphinxext.ipython_directive",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",  # this MUST be after napoleon https://github.com/agronholm/sphinx-autodoc-typehints/issues/15  # noqa
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Extension configuration -------------------------------------------------
# -- Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {"python": ("https://docs.python.org/3.8", None)}
