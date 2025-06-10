# Warning: This Lambda Function is deprecated and no longer supported

# Coralogix-MongoDB-Atlas

Collects and pushes MongoDB Atlas cluster logs, metrics (as logs), events, and alerts to Coralogix.

To deploy this integration you'll need the following:

* **MongoDB Atlas** Project with a compatible Cluster
    * Can't be M0 (Free), M2/M5 (Shared)
    * Full details of Cluster type limitations: [MongoDB Atlas Docs](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/#service-m0--free-cluster---m2--and-m5-limitations)
* **MongoDB Atlas** Project API key with at minimum "Project Data Access Read Write" permissions. 
    * Not a key from "Data API"
* **Coralogix** Account and associated Region and Private Key

## Installation
This MongoDB Atlas integration can be deployed by clicking the link below and signing into your AWS account:
[Deployment link](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-MongoDB-Atlas)

In the Application Settings, fill in the appropriate values:

## Fields

* **Application name** - The stack name of this application created via AWS CloudFormation.

* **NotificationEmail** - If the lambda's execute fails an auto email sends to this address to notify it via SNS (requires you have a working SNS, with a validated domain).

* **ApplicationName** - The name of the Coralogix application you wish to assign to this lambda.

* **CoralogixRegion** - The Coralogix location region, possible options are ``Europe``, ``Europe2``, ``India``, ``Singapore``, ``US``, ``US2``.

* **Enabled** - MongoDB Atlas API pulling state

* **FunctionArchitecture** - Lambda function architecture, possible options are ``x86_64``, ``arm64``.

* **FunctionMemorySize** - Do not change! This is the maximum allocated memory that this lambda can consume, the default is ``1024``.

* **FunctionTimeout** - Do not change! This is the maximum time in seconds the function may be allowed to run, the default is ``300``.

* **MongoDBAtlasClusterName** - MongoDB Atlas Cluster Name

* **MongoDBAtlasMetricsGranularity** - MongoDB Atlas Cluster Metrics granularity

* **MongoDBAtlasPrivateKey** - MongoDB Atlas API Private Key. Needs to have Read/Write permissions to the Project listed below.

* **MongoDBAtlasProjectName** - MongoDB Atlas Project Name.

* **MongoDBAtlasPublicKey** - MongoDB Atlas API Public Key. Found under Project - Access Manager, API Keys. Needs to have Read/Write permissions to the Project listed above.

* **MongoDBAtlasResources** - MongoDB Atlas Resources to collect.

* **PrivateKey** - Your Coralogix secret key. Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

* **Schedule** - MongoDB Atlas API pulling schedule. In [AWS Cloudwatch "rate" format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions) Default: rate(5 minute)

* **SubsystemName** - The subsystem name you wish to allocate to this log shipper.


## License

This project is licensed under the Apache-2.0 License.
