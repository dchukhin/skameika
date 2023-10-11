Skameika
========================

Below you will find basic setup and deployment instructions for the skameika
project. To begin you should have the following applications installed on your
local development system:

- Python >= 3.5
- NodeJS >= 4.2
- npm >= 2.14.7
- `pip <http://www.pip-installer.org/>`_ >= 1.5
- `virtualenv <http://www.virtualenv.org/>`_ >= 1.10
- `virtualenvwrapper <http://pypi.python.org/pypi/virtualenvwrapper>`_ >= 3.0
- Postgres >= 9.3
- git >= 1.7

A note on NodeJS 4.2 for Ubuntu users: this LTS release may not be available through the
Ubuntu repository, but you can configure a PPA from which it may be installed::

    curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
    sudo apt-get install -y nodejs

You may also follow the manual instructions if you wish to configure the PPA yourself:

    https://github.com/nodesource/distributions#manual-installation

Django version
------------------------

The Django version configured in this template is conservative. If you want to
use a newer version, edit ``requirements/base.txt``.

Getting Started
------------------------

First clone the repository from Github and switch to the new directory::

    $ git clone git@github.com:dchukhin/skameika.git
    $ cd skameika

To setup your local environment you can use the quickstart make target `setup`, which will
install both Python and Javascript dependencies (via pip and npm) into a virtualenv named
"skameika", configure a local django settings file, and create a database via
Postgres named "skameika" with all migrations run::

    $ make setup
    $ workon skameika

If you require a non-standard setup, you can walk through the manual setup steps below making
adjustments as necessary to your needs.

To setup your local environment you should create a virtualenv and install the
necessary requirements::

    # Check that you have python3.5 installed
    $ which python3.5
    $ mkvirtualenv skameika -p `which python3.5`
    (skameika)$ pip install -r requirements/dev.txt
    (skameika)$ npm install

Next, install pre-commit::

    $ pre-commit clean
    $ pre-commit install


Next, we'll set up our local environment variables. We use `django-dotenv
<https://github.com/jpadilla/django-dotenv>`_ to help with this. It reads environment variables
located in a file name ``.env`` in the top level directory of the project. The only variable we need
to start is ``DJANGO_SETTINGS_MODULE``::

    (skameika)$ cp skameika/settings/local.example.py skameika/settings/local.py
    (skameika)$ echo "DJANGO_SETTINGS_MODULE=skameika.settings.local" > .env

Create the Postgres database and run the initial migrate::

    (skameika)$ createdb -E UTF-8 skameika
    (skameika)$ python manage.py migrate

If you want to use `Travis <http://travis-ci.org>`_ to test your project,
rename ``project.travis.yml`` to ``.travis.yml``, overwriting the ``.travis.yml``
that currently exists.  (That one is for testing the template itself.)::

    (skameika)$ mv project.travis.yml .travis.yml

Development
-----------

You should be able to run the development server via the configured `dev` script::

    (skameika)$ npm run dev

Or, on a custom port and address::

    (skameika)$ npm run dev -- --address=0.0.0.0 --port=8020

Any changes made to Python, Javascript or Less files will be detected and rebuilt transparently as
long as the development server is running.


Automated Accessibility Tests
-----------------------------

This project has been set up to run automated accessibility tests,
which require [geckodriver](https://github.com/mozilla/geckodriver/).

To install on Linux:

```
$ curl -L https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz > geckodriver.tar.gz
$ tar -zxvf geckodriver.tar.gz
$ sudo mv geckodriver /usr/local/bin
```

To install on Mac:

```
$ brew install geckodriver
```

The accessibility tests will run as a part of the standard Python tests (``python manage.py test``).


Database Reset
--------------

To create a database dump, use the ``pg_dump`` command::

    (skameika)$ pg_dump --no-owner --no-privileges --clean --exclude-table-data django_session skameika --file db.dump

To load the database dump into a fresh database, use the ``psql`` command::

    (skameika)$ psql --dbname skameika --file db.dump


Deployment
----------

The deployment of requires Fabric but Fabric does not yet support Python 3. You
must either create a new virtualenv for the deployment::

    # Create a new virtualenv for the deployment
    $ mkvirtualenv skameika-deploy -p `which python2.7`
    (skameika-deploy)$ pip install -r requirements/deploy.txt

or install the deploy requirements
globally::

    $ sudo pip install -r requirements/deploy.txt


You can deploy changes to a particular environment with
the ``deploy`` command::

    $ fab staging deploy

New requirements or migrations are detected by parsing the VCS changes and
will be installed/run automatically.
