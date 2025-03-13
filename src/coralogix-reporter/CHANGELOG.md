# Changelog

## coralogix-reporter

### 3.0.0 / 13.03.2025
* [Fix] Rewrite the function from callback to async/await. This will resolve a critical issue, where the Lambda exits before the e-mail is being sent
* [Update] Replace API endpoints + CX region names to the new ones
* [Update] Rewrite the API logic to fit the new OpenSearch endpoints – default var + authorization header
* [Feature] Improve templating by parsing the API response's JSON and exit the function on empty result of templating
* [Fix] Add more logs and error handling to make the function easier to troubleshoot in case when it's not working as expected
* [Feature] Rake the search index configurable
* [Fix] Remove the unused IAM policy from the SAM template
* [Update] Upgrade nodejs from 20.x to 22.x
* [Update] Upgrade dependencies

### 2.0.2 / 1.03.2024
* [Fix] Add semantic versioning

### 2.0.1 / 1.03.2024
* [Fix] Add SES sendmail policy to lambda function

### 2.0.0 / 12.12.2023
* [Update] moved from elasticsearch to opensearch, namechange to coralogix-reporter
* [Update] upgrade nodejs from 16.x to 20.x
