#!/usr/local/bin/python3
import auto_posture_evaluator

def lambda_handler(event, context):
    tester = auto_posture_evaluator.AutoPostureEvaluator()
    tester.run_tests()

if __name__ == "__main__":
    auto_posture_evaluator.AutoPostureEvaluator().run_tests()
