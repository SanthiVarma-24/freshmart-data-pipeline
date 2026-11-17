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

echo "Deployment completed successfully."
echo "Finished: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"