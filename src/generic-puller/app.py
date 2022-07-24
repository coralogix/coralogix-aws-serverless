import logging
import time
import urllib.request as urlrequest
import urllib.error as urlerror
import json
import os, logging
from coralogix.handlers import CoralogixLogger

# Create internal logger and logs logger.
default_handlers = logging.root.handlers
logging.root.handlers = [logging.NullHandler()]
internal_logger = logging.getLogger("Internal Logger")
internal_logger.setLevel(logging.INFO)
internal_logger.handlers = default_handlers
external_logger = logging.getLogger("External Logger")
external_logger.setLevel(logging.INFO)
# Define environment variables
PRIVATE_KEY = os.getenv("CORALOGIX_PRIVATE_KEY")
APP_NAME = os.getenv("CORALOGIX_APPLICATION_NAME")
SUB_SYSTEM = os.getenv("CORALOGIX_SUBSYSTEM_NAME")
ENDPOINT = os.getenv("ENDPOINT")
LOGS_TO_STDOUT = os.getenv("LOGS_TO_STDOUT", "True")
SEND_TRUNCATED_LOGS = os.getenv("SEND_TRUNCATED_LOGS", "True")
LOGS_MAX_SIZE = os.getenv("LOGS_MAX_SIZE","32000")
AUTHORIZATION = os.getenv("AUTHORIZATION")
PAYLOAD = os.getenv("PAYLOAD")
METHOD = os.getenv("METHOD")
TRUE_VALUES = ["True","true"]

def lambda_handler(event, context):
    internal_logger.info("Generic puller lambda - init")
    # Environment variables check
    try:
        logs_max_size = int(LOGS_MAX_SIZE)
    except:
        internal_logger.error("Generic puller lambda Failure - could not convert to int logs_max_size")
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - could not convert to int logs_max_size",
            }),
        }
    if PAYLOAD != "":
        try:
            json.loads(PAYLOAD)
        except:
            internal_logger.error("Generic puller lambda Failure - could not json parse PAYLOAD")
            return {
                "statusCode": 400,
                "body": json.dumps({
                "message": "Generic puller lambda Failure - could not json parse PAYLOAD",
                }),
            }
    if ENDPOINT == "":
        internal_logger.error("Generic puller lambda Failure - Endpoint not found")
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - Endpoint not found",
            }),
        }
    if METHOD not in ["GET", "POST", "PUT", "DELETE"]:
        internal_logger.error("Generic puller lambda Failure - Method not found")
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - Method not found",
            }),
        }
    if PRIVATE_KEY == "":
        internal_logger.error("Generic puller lambda Failure - coralogix private key not found")
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - coralogix private key not found",
            }),
        }
    if APP_NAME == "" or SUB_SYSTEM == "":
        internal_logger.error("Generic puller lambda Failure - coralogix application name and subsystem name not found")
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - coralogix application name and subsystem name not found",
            }),
        }
    
    # print to stdout/cloudwatch external logger's logs
    if LOGS_TO_STDOUT in TRUE_VALUES:
        external_logger.handlers = default_handlers
    # Coralogix Logger init
    coralogix_external_handler = CoralogixLogger(PRIVATE_KEY, APP_NAME, SUB_SYSTEM)
    # Add coralogix logger as a handler to the standard Python logger.
    external_logger.addHandler(coralogix_external_handler)
    internal_logger.info("Generic puller lambda - init complete")
    domain = ENDPOINT.split("/")[2]
    # Create the request with all its parameters
    request = urlrequest.Request(ENDPOINT,method=METHOD)
    if AUTHORIZATION != "":
        request.add_header("Authorization","%s" % AUTHORIZATION)
    if PAYLOAD != "" and METHOD in ["POST","PUT"]:
        request.add_header("Content-Type", "application/json")
        request.data = PAYLOAD.encode('utf-8')
    request.add_header("User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:33.0) Gecko/20100101 Firefox/33.0")
    request.add_header("host",domain)
    try:
        response = urlrequest.urlopen(request, timeout=15)
        # Send the body of the response to coralogix
        log_sender(response, logs_max_size)
    except urlerror.HTTPError as e:
        internal_logger.error("Generic puller lambda Failure - Endpoint: %s , error: %s" % (ENDPOINT, e))
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - Endpoint: %s , error: %s" % (ENDPOINT, e)
            }),
        }
    except urlerror.URLError as e:
        internal_logger.error("Generic puller lambda Failure - Endpoint: %s , error: %s" % (ENDPOINT, e))
        return {
            "statusCode": 400,
            "body": json.dumps({
            "message": "Generic puller lambda Failure - Endpoint: %s , error: %s" % (ENDPOINT, e)
            }),
        }
    CoralogixLogger.flush_messages()
    time.sleep(1) # for now until fixing python sdk not fully flushing within aws lambda
    internal_logger.info("Generic puller lambda Success - logs sent to coralogix")
    return {
    "statusCode": 200,
    "body": json.dumps({
    "message": "Generic puller lambda Success - logs sent to coralogix",
    }),
    }

def log_sender(response, logs_max_size):
    res_body = response.read()
    string_size = len(res_body)
    res_body_decoded = res_body.decode('utf-8')
    # Big response logic
    if string_size > logs_max_size:
        if SEND_TRUNCATED_LOGS in TRUE_VALUES:
            if res_body_decoded.isascii():
                truncate_end = 31900
            else:
                truncate_end = int(logs_max_size * 0.90)
            log = res_body_decoded[0:truncate_end]
            log_dict = {"log":json.dumps(log),"truncated": "true"}
            external_logger.info(json.dumps(log_dict))
        return # return either way if string size is bigger than logs_max_size
    external_logger.info(res_body_decoded)