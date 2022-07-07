#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import boto3
import cfnresponse


print("Loading function")
s3 = boto3.client('s3')


def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))
    try:
        print("Request Type:", event['RequestType'])
        BucketNotificationConfiguration = s3.get_bucket_notification_configuration(
            Bucket=event['ResourceProperties']['Bucket']
        )
        BucketNotificationConfiguration.pop('ResponseMetadata')
        BucketNotificationConfiguration.setdefault('LambdaFunctionConfigurations', [])

        if event['RequestType'] in ['Update', 'Delete']:
            BucketNotificationConfiguration['LambdaFunctionConfigurations'] = list(
                filter(
                    lambda configuration: configuration.get('Id') != event['PhysicalResourceId'],
                    BucketNotificationConfiguration['LambdaFunctionConfigurations']
                )
            )

        if event['RequestType'] in ['Create', 'Update']:
            BucketNotificationConfiguration['LambdaFunctionConfigurations'].append({
                'Id': event.get('PhysicalResourceId', context.aws_request_id),
                'LambdaFunctionArn': event['ResourceProperties']['LambdaArn'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix',
                                'Value': event['ResourceProperties'].get('Prefix', '')
                            },
                            {
                                'Name': 'suffix',
                                'Value': event['ResourceProperties'].get('Suffix', '')
                            },
                        ]
                    }
                },
                'Events': [
                    's3:ObjectCreated:*'
                ]
            })

        if len(BucketNotificationConfiguration['LambdaFunctionConfigurations']) == 0:
            BucketNotificationConfiguration.pop('LambdaFunctionConfigurations')

        s3.put_bucket_notification_configuration(
            Bucket=event['ResourceProperties']['Bucket'],
            NotificationConfiguration=BucketNotificationConfiguration
        )
        responseStatus = cfnresponse.SUCCESS
        print(event['RequestType'], "request completed....")
    except Exception as e:
        print("Failed to process:", e)
        responseStatus = cfnresponse.FAILED
    finally:
        print("Sending response to custom resource")
        cfnresponse.send(
            event,
            context,
            responseStatus,
            {},
            event.get('PhysicalResourceId', context.aws_request_id)
        )
