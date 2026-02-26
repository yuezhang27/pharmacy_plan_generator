terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# VPC (minimal for RDS + Lambda)
# -----------------------------------------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-igw" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone        = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch  = true
  tags                    = { Name = "${var.project_name}-public-${count.index + 1}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = aws_subnet.public[*].id
  tags       = { Name = "${var.project_name}-db-subnet" }
}

# -----------------------------------------------------------------------------
# Security Groups
# -----------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id     = aws_vpc.main.id
  description = "RDS PostgreSQL"
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow from anywhere for migrations (restrict in prod)"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project_name}-rds-sg" }
}

resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  vpc_id     = aws_vpc.main.id
  description = "Lambda functions"
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project_name}-lambda-sg" }
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL
# -----------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"
  db_name        = var.db_name
  username       = var.db_username
  password       = var.db_password

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = false

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = true

  skip_final_snapshot = true
  tags               = { Name = "${var.project_name}-db" }
}

# -----------------------------------------------------------------------------
# SQS + DLQ
# -----------------------------------------------------------------------------
resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-dlq"
  tags = { Name = "${var.project_name}-dlq" }
}

resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-queue"
  visibility_timeout_seconds  = 120
  message_retention_seconds   = 86400
  receive_wait_time_seconds   = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "${var.project_name}-queue" }
}

# -----------------------------------------------------------------------------
# IAM
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_sqs" {
  name   = "${var.project_name}-lambda-sqs"
  role   = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.main.arn
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.main.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Functions
# 部署前必须先运行: python scripts/build_lambdas.py
# -----------------------------------------------------------------------------
locals {
  lambda_zips = {
    create_order     = "${path.module}/build/create_order.zip"
    generate_careplan = "${path.module}/build/generate_careplan.zip"
    get_order        = "${path.module}/build/get_order.zip"
  }
}

locals {
  db_host     = aws_db_instance.main.address
  db_port     = aws_db_instance.main.port
  db_endpoint = "${aws_db_instance.main.address}:${aws_db_instance.main.port}"
  lambda_env = {
    DB_HOST     = local.db_host
    DB_PORT     = tostring(local.db_port)
    DB_NAME     = var.db_name
    DB_USER     = var.db_username
    DB_PASSWORD = var.db_password
    SQS_QUEUE_URL = aws_sqs_queue.main.url
  }
}

resource "aws_lambda_function" "create_order" {
  filename         = local.lambda_zips.create_order
  function_name    = "${var.project_name}-create-order"
  role             = aws_iam_role.lambda.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = filebase64sha256(local.lambda_zips.create_order)
  depends_on       = [aws_db_instance.main]

  environment {
    variables = local.lambda_env
  }

  # 不配置 VPC：Lambda 默认有互联网访问，可连 RDS(public) 和 SQS
}

resource "aws_lambda_function" "generate_careplan" {
  filename         = local.lambda_zips.generate_careplan
  function_name    = "${var.project_name}-generate-careplan"
  role             = aws_iam_role.lambda.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 120
  source_code_hash = filebase64sha256(local.lambda_zips.generate_careplan)
  depends_on       = [aws_db_instance.main]

  environment {
    variables = local.lambda_env
  }
}

resource "aws_lambda_function" "get_order" {
  filename         = local.lambda_zips.get_order
  function_name    = "${var.project_name}-get-order"
  role             = aws_iam_role.lambda.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = filebase64sha256(local.lambda_zips.get_order)
  depends_on       = [aws_db_instance.main]

  environment {
    variables = local.lambda_env
  }
}

# SQS triggers generate_careplan Lambda
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.generate_careplan.arn
  batch_size       = 1
}

# -----------------------------------------------------------------------------
# API Gateway
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "create_order" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.create_order.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_order" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.get_order.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_orders" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.create_order.id}"
}

resource "aws_apigatewayv2_route" "get_orders_id" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /orders/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_order.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_create_order" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_get_order" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
