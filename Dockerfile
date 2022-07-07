FROM python:3.9
ENV AWS_DEFAULT_REGION=eu-central-1
RUN mkdir -p /usr/src/app
RUN pip install awscli aws-sam-cli
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /usr/src/app
USER root
