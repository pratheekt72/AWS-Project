# Store resource ownership and lifecycle metadata
resource "aws_dynamodb_table" "resource_metadata" {
  name         = "${var.name_prefix}-resource-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "resource_id"

  attribute {
    name = "resource_id"
    type = "S"
  }
}