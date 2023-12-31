# app/Dockerfile

FROM python:3.9-slim

# set work directory
WORKDIR /usr/src/app

COPY ./requirements.txt /tmp/requirements.txt
RUN apt-get update\
    && pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt \
    && pip cache purge \
    && rm -rf /root/.cache/pip


COPY ./app/ /usr/src/app/
COPY ./logo.png /usr/src/app/logo.png


ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]