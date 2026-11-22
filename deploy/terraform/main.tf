provider "aws" {
  region = "eu-central-1"
}

variable "db_password" {
  description = "Core DB master password (supplied at apply time, never committed)"
  type        = string
  sensitive   = true
}

variable "allowed_cidr" {
  description = "Internal CIDR range allowed to reach the Core API"
  type        = string
  default     = "10.0.0.0/16"
}

resource "aws_security_group" "core_api" {
  name        = "aurora-core-api"
  description = "Aurora Core API"

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }
}

resource "aws_s3_bucket" "statements" {
  bucket = "aurora-customer-statements"
  acl    = "private"
}

resource "aws_db_instance" "core" {
  identifier          = "aurora-core-db"
  engine              = "postgres"
  instance_class      = "db.t3.medium"
  allocated_storage   = 50
  username            = "aurora"
  password            = var.db_password
  storage_encrypted   = true
  publicly_accessible = false
  skip_final_snapshot = true
}
