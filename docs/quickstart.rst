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
 - `Make <make_>`_ (only for developper installation)


************
Installation
************

The easiest way to install the library is by using :code:`pip`:

.. code-block:: console

  $ pip install git+https://github.com/ludaavics/pogam.git

Verify your installation ...

.. code-block:: console

  $ pogam --version
  pogam, version 0.1.0


Alternatively, if you want to modify the library, you can do a developper
install and initialize the project using the provided :code:`make` recipe:

.. code-block:: console

  $ git clone https://github.com/ludaavics/pogam.git
  $ cd pogam
  $ make init
  $ pip install -e .

*************
Configuration
*************

By default, the scrape results are saved in a SQLite database stored in the
:code:`.pogam/` folder of your user directory. You can point to a different
database by setting the :code:`POGAM_DATABASE_URL` environment variable to
a valid `database URL <db_url_>`_.

By default, the scraped photos are saved in the :code:`.pogam/images/` folder of
your user directory. You can point to a different folder by setting the
:code:`POGAM_IMAGES_FOLDER` environment variable.

******
Usage
******

Command Line
============

You can kick off a scrape directly from the command line:

.. code-block:: console

  $ pogam scrape rent 75009 75010
  Scraping seloger...
  ...

Because the process can take a long time, it is often useful to turn on
verbose output:

.. code-block:: console

  $ pogam -v DEBUG scrape rent 75009 75010 --min-price=1000
  Scraping seloger...
  Starting the scrape of 12 listings fetched from https://www.seloger.com/list.html?projects=2&types=1,2&places=[{cp:75009}|{cp:75010}]&price=0/NaN&surface=0/NaN&rooms=0,1,2,3,4,5,6,7,8,9&bedrooms=2,3,4,5,6,7,8&enterprise=0&qsVersion=1.0&natures=1,2 .
  Scraping https://www.seloger.com/annonces/achat/appartement/paris-10eme-75/louis-blanc-aqueduc/153106473.htm ...
  Scraping https://www.seloger.com/annonces/achat/appartement/paris-10eme-75/louis-blanc-aqueduc/150587457.htm ...
  Scraping https://www.seloger.com/annonces/achat/appartement/paris-9eme-75/lorette-martyrs/145989607.htm ...
  ...

You can list all the supported query options with :code:`pogam scrape --help`:

.. code-block:: console

  $ pogam scrape --help
  Usage: pogam scrape [OPTIONS] TRANSACTION [POST_CODES]...

    Scrape offers for a TRANSACTION in the given POST_CODES.

    TRANSACTION is 'rent' or 'buy'. POSTCODES are postal or zip codes of the
    search.

  Options:
    --type [apartment|house|parking|store]
                                    Type of property.
    --min-price FLOAT               Minimum property price.
    --max-price FLOAT               Maximum property price.
    --min-size FLOAT                Minimum property size, in square meters.
    --max-size FLOAT                Maximum property size, in square meters.
    --min-rooms FLOAT               Minimum number of rooms.
    --max-rooms FLOAT               Maximum number of rooms.
    --min-beds FLOAT                Minimum number of bedrooms.
    --max-beds FLOAT                Maximum number of bedrooms.
    --num-results INTEGER           Approximate maximum number of listings to
                                    add to the database.  [default: 100]
    --max-duplicates INTEGER        Stop further scrapes once we see this many
                                    consecutive results that are already in the
                                    database.
    --sources [seloger]             Sources to scrape.
    --help                          Show this message and exit.


Library
=======

Alternatively, you can use Pogam as a library in your Python code:

.. ipython::
  :suppress:

  In [7]: import os

  In [7]: try:
     ...:   os.remove("../docs/_build/db.sqlite")
     ...: except FileNotFoundError:
     ...:   pass

  In [7]: os.environ["POGAM_DATABASE_URL"] = "sqlite:///../docs/_build/db.sqlite"

  In [7]: import logging; logger = logging.getLogger(); logger.setLevel(logging.INFO)


.. ipython::

  In [7]: from pogam import create_app, db, scrapers

  In [8]: app = create_app()

  In [9]: with app.app_context():
     ...:     results = scrapers.seloger("rent", "92130", min_size=29, max_size=31)
     ...:     db.session.commit()
     ...:     print(results)
     ...:     print(results['added'][0].to_dict() if results['added'] else None)

Check out the :doc:`API <api>` section for a complete reference.


****************
Scheduled Tasks
****************

The command line tool can be used with a task scheduler to periodically fetch
new listings matching criteria of interest. For example, let's set up a
`cron`_ job that will look for 2 bedrooms for sale in the 9th *arrondissement*
for less than 800,000€ every hour on the hour. Open your crontab file..

.. code-block:: console

  $ crontab -e

... and add the following line

.. code-block:: bash

  0 * * * * pogam scrape buy 75009 --min-beds=2 --max-price=800000



.. _conda: https://docs.conda.io/en/latest/
.. _cron : https://en.wikipedia.org/wiki/Cron
.. _db_url: https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
.. _git: https://git-scm.com/
.. _make: https://en.wikipedia.org/wiki/Make_(software)
.. _pip: https://pip.pypa.io/en/stable/
