FROM python:3.10.5-buster

# Required environment variables with some recommended defaults
# Requires mounting the datadir to /usr/src/app/data
ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    CYTOSCAPE_DATADIR=/root/data \
    CYTOSCAPE_BASEURL=http://cy:1234/v1 \
    NPATLAS_FILE=/usr/src/app/data/atlas_input/NPAtlas_download.json \
    COCONUT_FILE=/usr/src/app/data/atlas_input/COCONUT_download.json \
    REDIS_URI=redis://redis:6379/0 \
    SNAPMS_DATADIR=/usr/src/app/data

WORKDIR /usr/src/app

RUN pip install "poetry==$POETRY_VERSION"
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-interaction --no-ansi
 
COPY manage.py .
COPY snapmf_site /usr/src/app/snapmf_site
COPY snapmf /usr/src/app/snapmf

EXPOSE 8000
CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]
