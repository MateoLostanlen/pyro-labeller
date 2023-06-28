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


COPY ./task_manager.py /usr/src/app/task_manager.py


ENTRYPOINT ["python", "task_manager.py"]