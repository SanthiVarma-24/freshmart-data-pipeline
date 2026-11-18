#!/usr/bin/env bash

# FreshMart Analytics - AWS Lambda Deployment Script
#
# Usage:
#   bash scripts/deploy.sh FUNCTION_NAME ZIP_FILE
#
# Example:
#   bash scripts/deploy.sh csv_reader_lambda \
#       dist/csv_reader_lambda.zip
#
# Requirements:
#   - AWS CLI configured with deployment permissions
#   - Target Lambda function already created
#   - ZIP package built for the AWS Lambda Python runtime

set -euo pipefail

FUNCTION_NAME="${1:?Error: Lambda function name is required}"
ZIP_FILE="${2:?Error: ZIP file path is required}"

AWS_REGION="${AWS_REGION:-ap-south-2}"

if [[ ! -f "$ZIP_FILE" ]]; then
    echo "ERROR: ZIP file not found: $ZIP_FILE"
    exit 1
fi

echo "========================================"
echo "FreshMart Lambda Deployment"
echo "========================================"
echo "Function: $FUNCTION_NAME"
echo "Package: $ZIP_FILE"
echo "Region: $AWS_REGION"
echo "Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# Update the Lambda function's deployment package.
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$AWS_REGION" \
    --query '{FunctionName:FunctionName,LastUpdateStatus:LastUpdateStatus}' \
    --output json

# Wait until the function update completes.
aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"

# Publish a new version and update the live alias
# only for the durable orchestrator.
if [[ "$FUNCTION_NAME" == "pipeline_orchestrator" ]]; then
    echo "Publishing a new orchestrator version..."

    NEW_VERSION=$(aws lambda publish-version \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Version' \
        --output text)

    echo "Published version: $NEW_VERSION"
    echo "Updating live alias..."

    aws lambda update-alias \
        --function-name "$FUNCTION_NAME" \
        --name live \
        --function-version "$NEW_VERSION" \
        --region "$AWS_REGION" \
        --query '{Alias:Name,FunctionVersion:FunctionVersion}' \
        --output json

    echo "Live alias now points to version $NEW_VERSION"
fi

echo "Deployment completed successfully."
echo "Finished: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"