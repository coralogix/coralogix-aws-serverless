# Cross-account solutions

This table describes all possible solutions to fetch the info about Lambda functions and EC2 instances from multiple accounts.

| Approach | Implementation Method | Pros | Cons | Complexity | Scalability | Permissions Required |
|----------|------------------------|------|------|------------|-------------|----------------------|
| 1. Static IAM Role List | Maintain a static list of account IDs in configuration. For each account, assume role with same name, then use Lambda API to list functions in each region. | • Simple to implement<br>• No dependencies on other services<br>• Works without management account | • Requires manual maintenance of account list<br>• No discovery of new accounts<br>• Difficult to scale | Low | Poor | • Cross-account IAM roles with Lambda:List* permissions |
| 2. AWS Config Aggregator | Create a Config aggregator in a delegated admin account. Use SelectResourceConfig API to run SQL-like query to get all Lambda functions across the organization in one call. | • Comprehensive resource discovery<br>• SQL-like query capability<br>• Automatically updates as resources change<br>• Works across entire organization | • Requires Config enabled in all accounts<br>• Cost associated with Config<br>• Setup overhead | Medium | Excellent | • Delegated administrator for Config<br>• Config recording enabled in all accounts |
| 3. Organizations API | Use OrganizationsClient to list all accounts in organization, then loop through each account, assume role, and list Lambda functions in each region. | • Complete account discovery<br>• Native AWS solution for organization structure<br>• One-time setup | • Requires management account or delegated admin<br>• May not work for all customers | Medium | Good | • Organizations API access<br>• Cross-account roles for Lambda functions |
| 4. Resource Explorer | Set up Resource Explorer indexes in each account. Create views that focus on Lambda resources. Query the views with filters for Lambda functions. | • Fast searching across regions<br>• Simple query interface<br>• Low latency | • Newer service, less mature<br>• Requires setup in each account<br>• Limited to one account without cross-account indexing | Medium | Medium | • Resource Explorer setup in each account<br>• Cross-account roles |
| 5. Resource Access Manager | Create resource shares for Lambda functions in each account. Access shared resources from central account to inventory them. | • Allows sharing resources across accounts<br>• Centralized management | • Not designed for resource discovery<br>• Primary purpose is sharing resources, not inventory | High | Poor | • RAM admin permissions<br>• Cross-account sharing setup |
| 6. Resource Groups Tagging API | Use GetResources API with resource type filter for Lambda functions in each account (requires assuming roles) and in each region. | • Simple API call<br>• No additional services needed<br>• Works with tags | • Limited to one account at a time<br>• Requires consistent tagging strategy<br>• Need to loop through accounts | Low | Good | • Tag:GetResources permission<br>• Cross-account roles |
| 7. CloudWatch Logs Insights | Query CloudWatch Logs across accounts to find log groups with naming pattern "/aws/lambda/", then extract function names from log group names. | • Lambda functions generate logs by default<br>• Can derive function details from log groups | • Indirect discovery method<br>• May miss functions with custom log settings | Medium | Medium | • CloudWatch Logs access<br>• Cross-account roles |
| 8. Lake Formation + Athena | Set up Lake Formation with crawlers to inventory AWS resources across accounts. Store data in central data lake and query with Athena SQL to find Lambda functions. | • Centralized data repository<br>• Powerful query capabilities<br>• Works across entire organization | • Complex setup<br>• Ongoing maintenance<br>• Additional costs | High | Excellent | • Lake Formation permissions<br>• Cross-account data catalog access |

# Implemented solutions:

1. Static IAM List
2. AWS Config

The rest can be implemented on demand.
