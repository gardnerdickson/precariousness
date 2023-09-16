
FROM python:3.11

WORKDIR /code

COPY ./requirements/common.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./static /code/static
COPY ./server /code/server

EXPOSE 8000
CMD uvicorn server.main:app --host 0.0.0.0 --port 8000
