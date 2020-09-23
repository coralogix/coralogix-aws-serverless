# Coralogix-Elasticsearch-Reporter

Generates reports from [Coralogix Elasticsearch API](https://coralogix.com/tutorials/elastic-api/) and send by email.

## Prerequisites

1. Verified [AWS SES](https://aws.amazon.com/ses/) email/domain (**Sender** parameter).
2. [Coralogix](https://coralogix.com/) private key (**PrivateKey** parameter).
3. Prepared [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/search.html) query (**Query** parameter).
4. Prepared [JMESPath](https://jmespath.org/) template for parsing Elasticsearch response (**Template** parameter).
5. Prepared [Schedule Expressions for CloudWatch Rules](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions) (**Schedule** parameter).

For example:

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