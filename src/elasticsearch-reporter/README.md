# Coralogix-Elasticsearch-Reporter

Generates reports from [Coralogix Elasticsearch API](https://coralogix.com/tutorials/elastic-api/) and send by email.

## Parameters

* **Sender** - verified [AWS SES](https://aws.amazon.com/ses/) email/domain (**Sender** parameter).
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **Enabled** - `true` when report is active and will be running the query and sent periodically or `false` when it is inactive.
* **PrivateKey** - can be found in your Coralogix account under `Settings` -> `Account` -> `API Access` -> `Elasticsearch API key`.
* **Query** - the [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/search.html) query.
* **Recipient** - a list of comma separated e-mails.
* **RequestTimeout** - the Elasticsearch query timeout.
* **Schedule** - [CloudWatch rules schedule expression](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions).
* **Subject** - report email subject line.
* **Template** - [JMESPath](https://jmespath.org/) expression to structure the Elasticsearch response.

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