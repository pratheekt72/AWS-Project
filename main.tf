 
terraform {
  required_version = ">= 1.5.0"
 
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
 
provider "aws" {
  region = "us-east-1"
}

resource "aws_sns_topic" "notifications" {
  name = "resource-accountability-notifications"
}
 
output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}