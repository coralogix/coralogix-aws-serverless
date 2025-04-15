# Changelog

## lambda-manager

## 2.0.6  / 15-04-2025
### 🧰 Bug fixes 🧰
- Remove from the default value of RegexPattern the backslash.
- Update the lambda code so it will be compatible with requests from Terraform.

## 2.0.5  / 17-02-2025
### 🧰 Bug fixes 🧰
- Remove wildcard from the lambda permission policy.
- Update lambda name to in format {{stack_name}}-LambdaFunction.

## 2.0.4  / 1-07-2024
### 🧰 Bug fixes 🧰
- Add config to boto3, so the lambda could handle ThrottlingException, update error handling in the lambda.

## 2.0.3  / 26-06-2024
### 💡 Enhancements 💡
- Add a new parameter LogGroupPermissionPreFix, when defined the lambda will not create permission for each log group, but 1 permission for the prefix defined in the parameter.

## 2.0.2  / 24-06-2024
### 💡 Enhancements 💡
- Update the lambda to trigger on creation if ScanOldLogGroups is set to true

## 2.0.1  / 04-2-2024
### 💡 Enhancements 💡
- Update lambda code so it will not require the allow all policy

## 2.0.0 🎉 / 02-20-2024
### 🛑 Breaking changes 🛑
- New CloudFormation Template does not deploy firehose stream as part of the deployment.
- New CloudFormation Temaplate does not create permissions for destination, check README.
- Environment Variable names changed.

### 🚀 New components 🚀
- Supports Lambda as a Destination
- scan all loggroups and process them.

<!-- To add a new entry write: -->
<!-- ### version / full date -->
<!-- * [Update/Bug fix] message that describes the changes that you apply -->