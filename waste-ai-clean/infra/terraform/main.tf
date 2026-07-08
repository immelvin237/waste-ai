terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ---- S3 bucket for anomaly / low-confidence images (versioned, private) ----
resource "aws_s3_bucket" "images" {
  bucket = "${var.project}-images-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket                  = aws_s3_bucket.images.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---- PostgreSQL RDS (db.t3.micro, single-AZ) ----
resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "Allow Postgres"
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project}-db"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "waste"
  username               = var.db_username
  password               = var.db_password
  multi_az               = false
  publicly_accessible    = true
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.db.id]
}

# ---- IAM role for Lambda (least privilege) ----
resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---- Lambda that validates and inserts sync payloads ----
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "sync" {
  function_name    = "${var.project}-sync"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 30
  environment {
    variables = {
      DB_HOST = aws_db_instance.postgres.address
      DB_NAME = "waste"
      DB_USER = var.db_username
      DB_PASS = var.db_password
    }
  }
}

# ---- HTTP API Gateway ----
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.sync.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "sync" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /sync"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
