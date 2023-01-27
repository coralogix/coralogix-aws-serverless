const parseArn = require('./resources').parseArn;

describe('ARN parser', () => {
    it('parses EC2 instance ARNs', () => {
        const [account_id, region, resourceType, resourceId] = parseArn("arn:aws:ec2:eu-west-1:11111:instance/i-123");
        expect(account_id).toEqual("11111");
        expect(region).toEqual("eu-west-1");
        expect(resourceType).toEqual("aws:ec2:instance");
        expect(resourceId).toEqual("i-123");
    });
    it('parses application ALB ARNs', () => {
        const [account_id, region, resourceType, resourceId] = parseArn("arn:aws:elasticloadbalancing:eu-west-1:11111:loadbalancer/app/foo/123");
        expect(account_id).toEqual("11111");
        expect(region).toEqual("eu-west-1");
        expect(resourceType).toEqual("aws:elasticloadbalancing:loadbalancer");
        expect(resourceId).toEqual("app/foo/123");
    });
    it('parses RDS DB ARNs', () => {
        const [account_id, region, resourceType, resourceId] = parseArn("arn:aws:rds:eu-west-1:11111:db:foo");
        expect(account_id).toEqual("11111");
        expect(region).toEqual("eu-west-1");
        expect(resourceType).toEqual("aws:rds:db");
        expect(resourceId).toEqual("foo");
    });
    it('parses Lambda ARNs', () => {
        const [account_id, region, resourceType, resourceId] = parseArn("arn:aws:lambda:us-east-2:22222222222:function:serverlessrepo-blabla");
        expect(account_id).toEqual("22222222222");
        expect(region).toEqual("us-east-2");
        expect(resourceType).toEqual("aws:lambda:function");
        expect(resourceId).toEqual("serverlessrepo-blabla");
    });
    it('parses ApiGateway RestAPI ARNs', () => {
        const [account_id, region, resourceType, resourceId] = parseArn("arn:aws:apigateway:us-east-2::/restapis/ak5hhy49ik");
        expect(account_id).toEqual("");
        expect(region).toEqual("us-east-2");
        expect(resourceType).toEqual("aws:apigateway:restapis");
        expect(resourceId).toEqual("ak5hhy49ik");
    });
});
