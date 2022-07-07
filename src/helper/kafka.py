#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import time
import boto3
import cfnresponse


client = boto3.client("lambda")


def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    responseStatus = "SUCCESS"
    physicalResourceId = event.get("PhysicalResourceId")

    try:
        print("Request Type:", event["RequestType"])
        if event["RequestType"] in ["Create", "Update"]:
            if event["RequestType"] == "Update":
                try:
                    print("EventSourceMapping recreation")
                    client.delete_event_source_mapping(UUID=physicalResourceId)
                    while True:
                        client.get_event_source_mapping(UUID=physicalResourceId)
                        time.sleep(10)
                except client.exceptions.ResourceNotFoundException:
                    pass

            response = client.create_event_source_mapping(
                FunctionName=event["ResourceProperties"]["Function"],
                BatchSize=int(event["ResourceProperties"]["BatchSize"]),
                StartingPosition=event["ResourceProperties"]["StartingPosition"],
                Topics=[
                    event["ResourceProperties"]["Topic"]
                ],
                SelfManagedEventSource={
                    "Endpoints": {
                        "KAFKA_BOOTSTRAP_SERVERS": event["ResourceProperties"]["Brokers"]
                    }
                },
                SourceAccessConfigurations=list([
                    {
                        "Type": "VPC_SUBNET",
                        "URI": "subnet:" + subnetId
                    } for subnetId in event["ResourceProperties"]["SubnetIds"]
                ]) + list([
                    {
                        "Type": "VPC_SECURITY_GROUP",
                        "URI": "security_group:" + securityGroupId
                    } for securityGroupId in event["ResourceProperties"]["SecurityGroupIds"]
                ])
            )

            physicalResourceId = response["UUID"]

            while True:
                response = client.get_event_source_mapping(UUID=physicalResourceId)
                if response["State"] in ["Enabled", "Disabled"]:
                    break
                time.sleep(10)

            print("EventSourceMapping successfully created")
        elif event["RequestType"] == "Delete":
            try:
                client.delete_event_source_mapping(UUID=physicalResourceId)
            except client.exceptions.ResourceNotFoundException:
                pass
            print("EventSourceMapping successfully deleted")

    except Exception as exc:
        print("Failed to process:", exc)
        responseStatus = "FAILED"
    finally:
        cfnresponse.send(event, context, responseStatus, {}, physicalResourceId)
