# Changelog

## resource-metadata-sqs

### 0.3.0 / 30.04.2025
* [Feature] Cross-account collection has multiple options now: AWS Config and Static Account List
* [Feature] Enable cross-account Eventbridge events reception by SQS queue
* [Feature] Filter functions by telemetry-exporter layer
* [Update] Split StaticIAM configuration between ACCOUNT_IDS and CROSSACCOUNT_IAM_ROLE_ARNS
* [Fix] Get rid of GetFunctionCommand to avoid security vulnerability related to this command (i.e. link to the source code in the command output)

### 0.2.0 / 02.04.2025
* [Feature] CDS-1996 Add support for multiple regions and accounts
* [Fix] Align line endings in js files to always add with semicolon (`;`)

### 0.1.4 / 19.02.2025
* [Fix] CDS-1876 Reduce EC2 batch size by half as default (50 --> 25) and let the user configure the chunk size

### 0.1.3 / 17.02.2025
* [Fix] CDS-1876 rewrite batch collection of EC2 instances to avoid exceeding the SQS message size limit

### 0.1.2 / 04.02.2025
* [Fix] Adjust CloudTrail S3 bucket name to fit the character limit (<=63 characters)

### 0.1.1 / 31.01.2025
* [Fix] Remove non-existent function from SAM template and hardcode message retention period to 1 hour instead of using the resource ttl.
* [Fix] Update GitHub Actions publish step to store multi-function SAM template.

### 0.1.0 / 28.01.2025
* First version
<!-- To add a new entry write: -->
<!-- ### version / full date -->
<!-- * [Update/Bug fix] message that describes the changes that you apply -->
