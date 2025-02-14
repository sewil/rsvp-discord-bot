FROM python:3.8-slim

WORKDIR /usr/src/app

RUN apt-get update
RUN apt-get install libmariadb3 libmariadb-dev

COPY . .
COPY .env .env

RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "main.py"]
