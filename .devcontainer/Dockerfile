FROM mcr.microsoft.com/devcontainers/python:3

RUN apt-get install gnupg2 -y

RUN python -m pip install --upgrade pip \
    && python -m pip install flit

ENV FLIT_ROOT_INSTALL=1

COPY pyproject.toml .
RUN touch README.md \
    && mkdir -p src/elxr_metrics \
    && python -m flit install --only-deps --deps develop \
    && rm -r pyproject.toml README.md src
