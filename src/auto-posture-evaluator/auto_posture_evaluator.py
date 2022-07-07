#!/usr/local/bin/python3
import asyncio
import datetime
import os
import uuid

import importlib
import sys
from grpclib.client import Channel
from model import SecurityReportTestResult, SecurityReportIngestionServiceStub, SecurityReportContext, SecurityReport, \
    SecurityReportTestResultResult
from model.helper import struct_from_dict
import concurrent.futures

testers_module_names = []
if not os.environ.get('TESTER_LIST'):
    for module in os.listdir(os.path.dirname(__file__) + '/testers'):
        if module.startswith('_') or module[-3:] != '.py':
            continue
        module_name = "testers." + module[:-3]
        testers_module_names.append(module_name)
        importlib.import_module(module_name)
else:
    tester_list = os.environ.get('TESTER_LIST').split(',')
    for module in tester_list:
        if module:
            module_realpath = os.path.realpath("testers/" + module + "_tester.py")
            if module_realpath.startswith(os.path.dirname(__file__) + '/testers'):
                module_name = "testers." + module + "_tester"
                testers_module_names.append(module_name)
                importlib.import_module(module_name)
            else:
                print("The requested tester " + module + " is outside the expected path")
                continue
del module


def _adapter(log_message):
    log_message["name"] = log_message.pop("test_name")
    log_message["result"] = log_message.pop("test_result")
    return log_message


def _to_model(log_message, start_time, end_time) -> "SecurityReportTestResult":
    converted_log_message = _adapter(log_message)
    additional_data = {}
    test_result = SecurityReportTestResultResult.TEST_FAILED
    if log_message["result"] == "no_issue_found":
        test_result = SecurityReportTestResultResult.TEST_PASSED
    for key in converted_log_message.keys():
        if not hasattr(SecurityReportTestResult, key) and converted_log_message[key]:
            additional_data[key] = converted_log_message[key]
    return SecurityReportTestResult(
        name=converted_log_message["name"],
        start_time=start_time,
        end_time=end_time,
        item=converted_log_message["item"],
        item_type=converted_log_message["item_type"],
        result=test_result,
        additional_data=struct_from_dict(additional_data)
    )


class AutoPostureEvaluator:
    def __init__(self):
        if not os.environ.get('API_KEY'):
            raise Exception("Missing the API_KEY environment variable. CANNOT CONTINUE")

        # Configuration for grpc endpoint
        endpoint = os.environ.get("CORALOGIX_ENDPOINT_HOST")  # eg.: ng-api-grpc.dev-shared.coralogix.net
        port = os.environ.get("CORALOGIX_ENDPOINT_PORT", "443")
        self.channel = Channel(host=endpoint, port=int(port), ssl=True)
        self.client = SecurityReportIngestionServiceStub(channel=self.channel)
        self.api_key = os.environ.get('API_KEY')
        self.tests = []
        self.application_name = os.environ.get('APPLICATION_NAME', 'NO_APP_NAME')
        self.subsystem_name = os.environ.get('SUBSYSTEM_NAME', 'NO_SUB_NAME')
        self.batch_size = 2000
        self.regions = []
        if not os.environ.get('REGION_LIST'):
            self.regions = ['eu-north-1', 'ap-south-1', 'eu-west-3', 'eu-west-2', 'eu-west-1', 'ap-northeast-3'
                ,'ap-northeast-2', 'ap-northeast-1', 'sa-east-1', 'ap-southeast-1'
                , 'ap-southeast-2', 'eu-central-1', 'us-east-1', 'us-east-2', 'us-west-1'
                ,'us-west-2','af-south-1','ap-east-1','ca-central-1'
                ,'eu-south-1','me-south-1','global']
        else:
            self.regions = os.environ.get('REGION_LIST').split(',')
        for tester_module in testers_module_names:
            if "Tester" in sys.modules[tester_module].__dict__:
                self.tests.append(sys.modules[tester_module].__dict__["Tester"])

    def run_single_test(self, cur_tester, execution_id,loop):
        events_buffer = []
        cur_test_start_timestamp = datetime.datetime.now()
        #print("INFO: Start " + str(cur_tester.declare_tested_service()) + " tester")
        #try:
        tester_result = cur_tester.run_tests()
        cur_test_end_timestamp = datetime.datetime.now()
        # except Exception as exTesterException:
        #     print("WARN: The tester " + cur_tester.declare_tested_service() + " has crashed with the following exception during 'run_tests()'. SKIPPED: " +
        #         str(exTesterException))
        #     return
        error_template = "The result object from the tester " + cur_tester.declare_tested_service() + \
                         " does not match the required standard"
        if tester_result is None:
            print(error_template + " (ResultIsNone).")
            return
        if not isinstance(tester_result, list):
            print(error_template + " (NotArray).")
            return
        if not tester_result:
            #print(error_template + " (Empty array).")
            return
        else:
            for result_obj in tester_result:
                if "timestamp" not in result_obj or "item" not in result_obj or "item_type" \
                        not in result_obj or "test_result" not in result_obj:
                    print(error_template + " (FieldsMissing). CANNOT CONTINUE.")
                    continue
                if result_obj["item"] is None:
                    print(error_template + " (ItemIsNone). CANNOT CONTINUE.")
                    continue
                if not isinstance(result_obj["timestamp"], float):
                    print(error_template + " (ItemDateIsNotFloat). CANNOT CONTINUE.")
                    continue
                if len(str(int(result_obj["timestamp"]))) != 10:
                    print(error_template + " (ItemDateIsNotTenDigitsIntPart). CANNOT CONTINUE.")
                    continue
                events_buffer.append(_to_model(result_obj, cur_test_start_timestamp, cur_test_end_timestamp))

                if len(events_buffer) % self.batch_size == 0:
                    self.report_test_result(cur_tester, events_buffer.copy(), execution_id,loop)
                    events_buffer = []
        if len(events_buffer) > 0:
            self.report_test_result(cur_tester, events_buffer.copy(), execution_id,loop)

    def run_tests(self):
        loop = asyncio.get_event_loop()
        execution_id = str(uuid.uuid4())
        lambda_start_timestamp = datetime.datetime.now()
        for i in range(0, len(self.tests)):
            tester = self.tests[i]
            for region in self.regions:
                try:
                    cur_tester = tester(region)
                    print("INFO:Start tester " + cur_tester.declare_tested_service() +" for region "+region)
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.submit(self.run_single_test, cur_tester, execution_id,loop)
                except Exception as exTesterException:
                    print(
                        "WARN: The tester " + cur_tester.declare_tested_service() + " has crashed with the following exception during 'run_tests()'. SKIPPED: " +
                        str(exTesterException))
                    continue

        print("Lambda taken " + str(datetime.datetime.now() - lambda_start_timestamp))

    def report_test_result(self,  cur_tester, events_buffer, execution_id,loop):
        context = SecurityReportContext(
            provider=cur_tester.declare_tested_provider(),
            service=cur_tester.declare_tested_service(),
            execution_id=execution_id,
            application_name=self.application_name,
            computer_name="CoralogixServerlessLambda",
            subsystem_name=self.subsystem_name
        )
        report = SecurityReport(context=context, test_results=events_buffer)
        # print("DEBUG: Sent " + str(len(events_buffer)) + " events for " +
        #       cur_tester.declare_tested_service())
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.client.post_security_report(api_key=self.api_key, security_report=report))
        except Exception as ex:
            print("ERROR: Failed to send " + str(len(events_buffer)) + " events for tester " +
                  cur_tester.declare_tested_service() + " due to the following exception: " + str(ex))
        self.channel.close()

