##################
Developers' Guide
##################

This document is for developers that want to modify or contribute to the
project. It is written for macOS but should work for Linux.

.. contents::
  :local:
  :depth: 1
  :backlinks: none


*************
Requirements
*************

In addition to the :doc:`standard requirements <quickstart>`, we assume you
have the following installed:

  - `Make <make_>`_

.. note::

  For installation of :code:`make` on Windows, we recommend using the
  `Chocolatey <chocolatey_>`_ package manager for Windows.

.. _make: https://en.wikipedia.org/wiki/Make_(software)
.. _chocolatey: https://chocolatey.org/


************
Installation
************

The project ships with an initialization
recipe to set up a conda environment and a git pre-commit hook:

.. code-block:: console

  $ git clone git+https://github.com/ludaavics/pogam.git
  $ cd pogam
  $ make init

If you don't have :code:`make` installed, you can manually initialze the
project. From the project's folder:

.. code-block:: console

  $ conda env create --file .ci/environment.yml
  $ ln -s ../../.ci/pre-commit .git/hooks/pre-commit
