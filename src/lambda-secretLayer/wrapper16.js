const assert = require("assert");

async function getSecret() {
  //assert(process.env.SECRET_NAME, "No SECRET_NAME Variable!");

  const AWS = require('aws-sdk');
  
  AWS.config.update({region:process.env.AWS_REGION});
  const secretsManager = new AWS.SecretsManager();
  // const secretName = process.env.SECRET_NAME;
  const secretName = process.env.CUSTOME_SECRET_NAME || "lambda/coralogix/" + process.env.AWS_REGION + "/" + process.env.AWS_LAMBDA_FUNCTION_NAME;  console.log(secretName);
  const params = {
    SecretId: secretName
  };
  const secretData = await secretsManager.getSecretValue(params).promise();
  const secretValue = secretData.SecretString;
  const fs = require('fs');
  fs.writeFile("/tmp/envVars", "export private_key=" + secretValue, function(err) {
    if(err) {
        return console.log(err);
    }
    //console.log("The file was saved!");
}); 
  
}

getSecret();