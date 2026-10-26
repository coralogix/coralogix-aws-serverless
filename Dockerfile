FROM python:3.12
ENV AWS_DEFAULT_REGION=eu-central-1
RUN mkdir -p /usr/src/app
RUN pip install "awscli==1.46.2" "aws-sam-cli==1.170.0"
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /usr/src/app
USER root
