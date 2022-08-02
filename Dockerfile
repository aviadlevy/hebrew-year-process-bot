FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

RUN --mount=type=secret,id=ACCESS_KEY \
  --mount=type=secret,id=ACCESS_SECRET \
  --mount=type=secret,id=CONSUMER_KEY \
  --mount=type=secret,id=CONSUMER_SECRET \
  --mount=type=secret,id=SLACK_API_TOKEN \
  --mount=type=secret,id=BEARER_TOKEN \
   export ACCESS_KEY=$(cat /run/secrets/ACCESS_KEY) && \
   export ACCESS_SECRET=$(cat /run/secrets/ACCESS_SECRET) && \
   export CONSUMER_KEY=$(cat /run/secrets/CONSUMER_KEY) && \
   export CONSUMER_SECRET=$(cat /run/secrets/CONSUMER_SECRET) && \
   export SLACK_API_TOKEN=$(cat /run/secrets/SLACK_API_TOKEN) && \
   export BEARER_TOKEN=$(cat /run/secrets/BEARER_TOKEN)
