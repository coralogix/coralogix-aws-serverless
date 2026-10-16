#!/bin/bash
# This script will change the codeUri in a given template, so that the template will be validate
# for cloudformation.

template_file=$1
package_name=$2
README_file=$3
bucket_string="!Sub coralogix-serverless-repo-\${AWS::Region}"

# set_code_uri <resource> <zip key>: rewrite CodeUri of an existing resource to the
# packaged S3 location. Matching on the resource itself (not a substring of the file)
# keeps names like CollectorLambdaFunction from creating bogus LambdaFunction resources.
set_code_uri() {
    local resource=$1 key=$2
    if [[ "$(yq eval ".Resources.$resource" "$template_file")" == "null" ]]; then
        return
    fi
    yq eval '.Resources.'"$resource"'.Properties.CodeUri = {"Bucket": "'"$bucket_string"'", "Key": "'"$key"'"}' -i $template_file
    sed -i "s/'!Sub coralogix-serverless-repo-\${AWS::Region}/!Sub 'coralogix-serverless-repo-\${AWS::Region}/g" $template_file
}

set_code_uri LambdaFunction "$package_name.zip"
set_code_uri LambdaFunctionSM "$package_name.zip"
# resource-metadata-sqs ships two artifacts (see StoreMultiFunction in publish.yaml)
set_code_uri CollectorLambdaFunction "$package_name-collector.zip"
set_code_uri GeneratorLambdaFunction "$package_name-generator.zip"
set_code_uri GeneratorLambdaFunctionSM "$package_name-generator.zip"
if grep -q "CustomResourceLambdaTriggerFunction" "$template_file" && [[ $package_name != "vpc-flow-logs" ]]; then
    yq eval '.Resources.CustomResourceLambdaTriggerFunction.Properties.CodeUri = {"Bucket": "'"$bucket_string"'", "Key": "helper.zip"}' -i $template_file
    sed -i "s/'!Sub coralogix-serverless-repo-\${AWS::Region}/!Sub 'coralogix-serverless-repo-\${AWS::Region}/g" $template_file
fi
if grep -q "LambdaLayer" "$template_file" && [[ $package_name == "lambda-secretLayer" ]]; then
    yq eval '.Resources.LambdaLayer.Properties.ContentUri = {"Bucket": "'"$bucket_string"'", "Key": "'"$package_name"'.zip"}' -i $template_file
    sed -i "s/'!Sub coralogix-serverless-repo-\${AWS::Region}/!Sub 'coralogix-serverless-repo-\${AWS::Region}/g" $template_file
fi

sed -i "1s/^/#Created automatically from coralogix\/coralogix-aws-serverless\n#Link to the repo: https:\/\/github.com\/coralogix\/coralogix-aws-serverless\/tree\/master\/src\/$package_name\n/" $template_file

sed -i '/^## AWS Resource Manager Template Deployment$/,/^## Fields/c\
## Fields 
' $README_file

sed -i '3s/^/This template were created automatically from coralogix\/coralogix-aws-serverless.\nTo make a change in the template go to the link below.\n\n/' $README_file

sed -i "5s/^/\nhttps:\/\/github.com\/coralogix\/coralogix-aws-serverless\/tree\/master\/src\/$package_name\n/" $README_file
