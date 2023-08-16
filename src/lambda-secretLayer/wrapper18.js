const { SecretsManagerClient, GetSecretValueCommand } = require("@aws-sdk/client-secrets-manager");
const { writeFile } = require("fs");


async function getSecret() {
  const client = new SecretsManagerClient({ region: process.env.AWS_REGION });

  const secretName = process.env.SECRET_NAME || "lambda/coralogix/" + process.env.AWS_REGION + "/" + process.env.AWS_LAMBDA_FUNCTION_NAME;  console.log(secretName);
  
  const command = new GetSecretValueCommand({ SecretId: secretName });
  const secretData = await client.send(command);
  
  const secretValue = secretData.SecretString;
  writeFile("/tmp/envVars", "export private_key=" + secretValue, function(err) {
    if(err) {
      return console.log(err);
    }
    //console.log("The file was saved!");
  });

}

getSecret();
