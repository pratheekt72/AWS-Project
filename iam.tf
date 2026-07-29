# Let Lambda use this role
resource "aws_iam_role" "lambda_role" {
  name = "${var.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Let Lambda write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Let Lambda send messages to this SNS topic
resource "aws_iam_role_policy" "lambda_sns" {
  name = "${var.name_prefix}-lambda-sns"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sns:Publish"
      Resource = aws_sns_topic.notifications.arn
    }]
  })
}