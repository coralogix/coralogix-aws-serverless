import json
import boto3
import cfnresponse

print("Loading function")

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))
    try:        
        lambda_arn = event['ResourceProperties']['LambdaArn']
        lambda_client = boto3.client('lambda')

        if event['RequestType'] in ['Create', 'Update']:
            StringlogGroupName = event['ResourceProperties']['CloudwatchGroup']
            logGroupName = StringlogGroupName.split(',')
            cloudwatch_logs = boto3.client('logs')
            for log_group in logGroupName:
                cloudwatch_logs.put_subscription_filter(
                    destinationArn=event['ResourceProperties']['LambdaArn'],
                    filterName='lambda-cloudwatch-trigger',
                    filterPattern='',
                    logGroupName=log_group
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
