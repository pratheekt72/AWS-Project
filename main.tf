 

 
provider "aws" {
  region = "us-east-1"
}

resource "aws_sns_topic" "notifications" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol = "email"
  endpoint = "your-email@example.com"
}
 
output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}