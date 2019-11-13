################
Getting Started
################

This tutorial will give you a quick tour of the Pogam scraping library. It is
written for macOS but should work for Linux.

.. contents::
  :local:
  :depth: 1
  :backlinks: none

*************
Requirements
*************

Make sure you have the following installed:

 - `Git <git_>`_
 - `Pip <pip_>`_

For dev work, we assume you have the following installed:
  - `Make <make_>`_

************
Installation
************

The easiest way to install the library is by using :code:`pip`:

.. code-block:: bash

  $ pip install git+https://github.com/ludaavics/pogam.git

Verify your installation ...

.. code-block:: python

  import pogam
  print(pogam.__version__)


dev install
===========

If you want to modify the code or contribute to the project you will want
to clone the repository instead. The project ships with an initialization
recipe to set up a conda environment and a git pre-commit hook:

.. code-block:: bash

  $ git clone git+https://github.com/ludaavics/pogam.git
  $ cd pogam
  $ make init


If you don't have :code:`make` installed, you can initialize manually. From
the project's folder:

  $ conda env create --file .ci/environment.yml
  $ ln -s ../../.ci/pre-commit .git/hooks/pre-commit

*************
First search
*************

.. code-block:: python

  import pogam
  from pogam.scrape import seloger
  app = pogam.create_app()
  app.app_context().push()
  failed = pogam.scrape.seloger('rent', '92130')






.. _conda: https://docs.conda.io/en/latest/
.. _git: https://git-scm.com/
.. _make: https://en.wikipedia.org/wiki/Make_(software)
.. _pip: https://pip.pypa.io/en/stable/
