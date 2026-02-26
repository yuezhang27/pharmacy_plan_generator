output "api_url" {
  description = "API Gateway URL for Postman testing"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}"
}

output "post_orders_url" {
  description = "POST /orders endpoint"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/orders"
}

output "get_order_url" {
  description = "GET /orders/{id} endpoint (replace {id} with careplan id)"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/orders/"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (for migrations)"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "sqs_queue_url" {
  description = "SQS main queue URL"
  value       = aws_sqs_queue.main.url
}

output "sqs_dlq_url" {
  description = "SQS Dead Letter Queue URL"
  value       = aws_sqs_queue.dlq.url
}
