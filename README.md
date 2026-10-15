# snapms

core code for the SNAP MS platform for predicting identities of natural products from MS data

![SNAP-MS logo](snapms_logo_720.png "Logo")

## Installation

NEW - uses [Poetry Python](https://python-poetry.org/).
To setup local dev simply run `poetry install`

Requires Python 3.8+.

The `docker-compose` solution has been updated such that it should work with the following:

```bash
docker-compose build
docker-compose up -d
```

## Django App

This repo includes an example Django App for Snap MS. Some configuration is required.

Environment file (`.env`)

```.env
REDIS_URI=redis://localhost:6379/0
CYTOSCAPE_DATADIR=/root/data
SNAPMS_DATADIR=/home/username/git/snapms/data
NPATLAS_FILE=/home/username/git/snapms/data/atlas_input/NPAtlas_download.json
COCONUT_FILE=/home/username/git/snapms/data/atlas_input/COCONUT_download.json
```

The `SNAPMS_DATADIR` MUST exist already and the `NPATLAS_FILE` and `COCONUT_FILE` MUST also be available.

To run locally you must also create a DB directory 'db' as 'snapms/db'

Running the development server requires two instances. For each instance, open a terminal window, navigate to the root 'snapms' directory and type:

__1.__ Django App

```bash
dotenv run ./manage.py runserver
```

__2.__ RQ worker

```bash
dotenv run ./manage.py rqworker high default low
```

You must also have the following two Docker containers running locally:

## Requirements

__1.__ Redis - Docker

You can easily start Redis in a docker container locally with 

```bash
docker run -itd -p 6379:6379 --name snapmf-redis redis
```

__2.__ Cytoscape

Cytoscape automation requires a running instance. You can run it on the desktop, but on a server
it will be easier to run it in a docker container. The CyREST runs on port 1234.

For cytoscape session file serving to work, the mounted volume should point to the same place as the 
`SNAPMS_DATADIR`.

In development, using `./data` as the `SNAPMS_DATADIR` is sensible.

```bash
docker run --name cy -itd -v $(pwd)/data/testing:/root/data -p 1234:1234 jvansan/cytoscape-desktop-headless:latest
```

## Docker deployment

In this repo is a `docker-compose.yml` file which shows how to deploy this example app using Traefik as a reverse proxy.
In a real production environment, you should NOT use the build in Django `runserver`.
