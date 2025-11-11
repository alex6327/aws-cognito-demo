terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
}

# Zip up the Lambda source code (the "src" folder)
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "demo-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Attach basic execution policy (writes logs to CloudWatch)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# EXTRA: allow Lambda to call Cognito
resource "aws_iam_policy" "lambda_cognito_policy" {
  name        = "demo-lambda-cognito-policy"
  description = "Allow Lambda to call Cognito user pool APIs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:SignUp",
          "cognito-idp:InitiateAuth",
          "cognito-idp:AdminGetUser"
        ]
        Resource = "*"
        # later you can scope this to your specific user pool ARN
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_cognito_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_cognito_policy.arn
}

# The Lambda function itself
resource "aws_lambda_function" "demo" {
  function_name = "demo-terraform-lambda"

  role    = aws_iam_role.lambda_role.arn
  runtime = "python3.13"
  handler = "handler.lambda_handler"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      STAGE        = "dev"
      USER_POOL_ID = "us-west-2_VDOwh9vAJ"
      CLIENT_ID    = "70tt718drf44aidmqct9j61t5m"
    }
  }
}
# HTTP API in front of the Lambda
resource "aws_apigatewayv2_api" "http_api" {
  name          = "demo-http-api"
  protocol_type = "HTTP"
}

# Integrate API Gateway with Lambda (proxy)
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.demo.invoke_arn
  payload_format_version = "2.0"
}

# Route: POST /auth -> Lambda
resource "aws_apigatewayv2_route" "auth_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Default stage (auto deploy)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# Allow API Gateway to invoke the Lambda
resource "aws_lambda_permission" "allow_apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.demo.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

output "lambda_name" {
  value = aws_lambda_function.demo.function_name
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}