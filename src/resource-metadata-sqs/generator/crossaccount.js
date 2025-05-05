import { STSClient, AssumeRoleCommand, GetCallerIdentityCommand } from "@aws-sdk/client-sts";

export const assumeRole = async (roleArn) => {
    const stsClient = new STSClient({});
    const command = new AssumeRoleCommand({
        RoleArn: roleArn,
        RoleSessionName: 'CrossAccountLambdaSession'
    });
    const data = await stsClient.send(command);
    return {
        accessKeyId: data.Credentials.AccessKeyId,
        secretAccessKey: data.Credentials.SecretAccessKey,
        sessionToken: data.Credentials.SessionToken
    };
};

export const getAccountId = async () => {
    const stsClient = new STSClient({});
    const command = new GetCallerIdentityCommand({});
    const data = await stsClient.send(command);
    return data.Account;
};
