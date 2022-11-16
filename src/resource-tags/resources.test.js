const parseArn = require('./resources').parseArn;

describe('ARN parser', () => {
    it('parses EC2 instance ARNs', () => {
        const [resourceType, resourceId] = parseArn("arn:aws:ec2:eu-west-1:11111:instance/i-123");
        expect(resourceType).toEqual("aws:ec2:instance");
        expect(resourceId).toEqual("i-123");
    });
    it('parses application ALB ARNs', () => {
        const [resourceType, resourceId] = parseArn("arn:aws:elasticloadbalancing:eu-west-1:11111:loadbalancer/app/foo/123");
        expect(resourceType).toEqual("aws:elasticloadbalancing:loadbalancer");
        expect(resourceId).toEqual("app/foo/123");
    });
    it('parses RDS DB ARNs', () => {
        const [resourceType, resourceId] = parseArn("arn:aws:rds:eu-west-1:11111:db:foo");
        expect(resourceType).toEqual("aws:rds:db");
        expect(resourceId).toEqual("foo");
    });
});
