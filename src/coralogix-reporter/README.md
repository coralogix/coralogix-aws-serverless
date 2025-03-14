# Coralogix-Reporter

Generates report from [Coralogix OpenSearch API](https://coralogix.com/docs/opensearch-api/) and sends it by email.

## API Key

The API key can be created in your Coralogix account under `Data Flow` -> `API Keys` -> `Personal Keys`. It’s recommended to use the `DataQuerying` permission preset, as it is automatically updated with all relevant permissions.

## Parameters

* **CoralogixRegion** - possible values are `EU1`, `EU2`, `US1`, `US2`, `SG1`, `IN1`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **APIKey** - can be found in your Coralogix account under `Data Flow` -> `API Keys` -> `Personal Keys`.
* **Schedule** - [CloudWatch rules schedule expression](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions).
* **ScheduleEnable** - `true` when report is active and will be running the query and sent periodically or `false` when it is inactive.
* **Index** - the OpenSearch index to query. If you want to query logs, then use `*`. If you want to query Logs2Metrics, then use `*:*_log_metrics*`.
* **Query** - the [OpenSearch](https://opensearch.org/docs/latest/query-dsl/index/) query.
* **Template** - [JMESPath](https://jmespath.org/) expression to structure the OpenSearch response.
* **Sender** - verified [AWS SES](https://aws.amazon.com/ses/) email/domain (**Sender** parameter).
* **Recipient** - a list of comma separated e-mails.
* **Subject** - report email subject line.
* **RequestTimeout** - the OpenSearch query timeout.
* **NotificationEmail** - Failure notification email address.

## Usage

**query:**

```json
{"query":{"bool":{"must":[{"range":{"coralogix.timestamp":{"gte":"now-24h","lt":"now"}}}]}},"aggregations":{"applications":{"terms":{"field":"coralogix.metadata.applicationName"}}}}
```

**template:**

```
aggregations.applications.buckets[*].{application: key, logs: doc_count}
```

**result:**

```json
[
    {
        "application": "my_app1",
        "logs": 1
    },
    {
        "application": "my_app2",
        "logs": 5
    }
]
```

## License

This project is licensed under the Apache-2.0 License.
