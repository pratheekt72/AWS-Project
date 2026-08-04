# Package the Lambda code into a zip file
data "archive_file" "registration_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda/registration/handler.py"
  output_path = "${path.module}/registration_lambda.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "registration" {
  function_name = "${var.name_prefix}-registration-lambda"
  role          = aws_iam_role.lambda_role.arn

  runtime = "python3.12"
  handler = "handler.lambda_handler"

  filename         = data.archive_file.registration_lambda.output_path
  source_code_hash = data.archive_file.registration_lambda.output_base64sha256

  environment {
  variables = {
    SNS_TOPIC_ARN       = aws_sns_topic.notifications.arn
    DYNAMODB_TABLE_NAME = aws_dynamodb_table.resource_metadata.name
    LOG_LEVEL           = "INFO"
  }
}