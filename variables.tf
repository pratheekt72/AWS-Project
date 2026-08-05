variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix on every resource name so teammates don't collide in the shared account."
  type        = string
  default     = "name_prefix"
}
variable "notification_email" {
  description = "Email address to recieve SNS notfications"
  type        = string
}