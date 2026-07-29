 

 
provider "aws" {
  region = "us-east-1"
}

resource "aws_sns_topic" "notifications" {
  name = "${var.name_prefix}-resource-accountability"
}
 
output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}
resource "aws_sns_topic_subscription" "email_notifications" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol = "email"
  endpoint = var.notification_email 
}