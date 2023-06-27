import json
import boto3
import os
from coralogix.handlers import CoralogixLogger

ecr_client = boto3.client('ecr')
ssm_client = boto3.client('ssm')
parameterStore = os.getenv("SSM_PARAMETER_STORE_NAME")
privateKey = os.getenv("PRIVATE_KEY")

logger: CoralogixLogger = CoralogixLogger(privateKey, os.getenv("APPLICATION_NAME"), os.getenv("SUBSYSTEM_NAME"))


def lambda_handler(event, context):
    account_id = event['account']
    repo = event['detail']['repository-name']
    image = {"imageDigest": event['detail']["image-digest"], "imageTag": event['detail']["image-tags"][0]}

    # Initiate the DescribeImageScanFinding request, saving the response as a dictionary
    findings = ecr_client.describe_image_scan_findings(
        registryId=account_id,
        repositoryName=repo,
        imageId=image,
        maxResults=1000
    )

    # Iterate each finding and prepare for shipping to Coralogix
    for finding in findings['imageScanFindings']['findings']:
        log = {
            "ecr_image_scan": {
                "metadata": {
                    "repository": event['detail']['repository-name'],
                    "image_id": findings["imageId"]["imageDigest"],
                    "image_tag": event['detail']["image-tags"][0]
                },
                "findings": finding
            }
        }
        logger.log(3, json.dumps(log))
    logger.flush_messages()
