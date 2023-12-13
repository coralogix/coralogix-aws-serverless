# Coralogix-Reporter

Generates reports from [Coralogix OpenSearch API](https://coralogix.com/docs/opensearch-api/) and send by email.

## Parameters

* **Sender** - verified [AWS SES](https://aws.amazon.com/ses/) email/domain (**Sender** parameter).
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `US2`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **Enabled** - `true` when report is active and will be running the query and sent periodically or `false` when it is inactive.
* **LogsQueryKey** - can be found in your Coralogix account under `Data Flow` -> `API Access` -> `Logs Query Key`.
* **Query** - the [OpenSearch](https://opensearch.org/docs/latest/query-dsl/index/) query.
* **Recipient** - a list of comma separated e-mails.
* **RequestTimeout** - the OpenSearch query timeout.
* **Schedule** - [CloudWatch rules schedule expression](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions).
* **Subject** - report email subject line.
* **Template** - [JMESPath](https://jmespath.org/) expression to structure the OpenSearch response.

## Usage

**query:**

```json
{
    "query": {
        "bool": {
            "must":
            [
                {
                    "range": {
                        "coralogix.timestamp": {
                            "gte": "now-24h",
                            "lt": "now"
                        }
                    }
                }
            ]
        }
    },
    "aggs": {
        "applications": {
            "terms": {
                "field": "coralogix.metadata.applicationName"
            }
        }
    }
}
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
