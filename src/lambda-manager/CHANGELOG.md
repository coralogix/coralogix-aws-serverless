# Changelog

## lambda-manager

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