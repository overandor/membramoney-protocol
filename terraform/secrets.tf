resource "aws_secretsmanager_secret" "jwt" {
  name        = "membramoney/jwt-secret"
  description = "JWT signing secret"
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = var.jwt_secret
}

resource "aws_secretsmanager_secret" "pepper" {
  name        = "membramoney/hmac-pepper"
  description = "HMAC pepper for PIN hashing"
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "pepper" {
  secret_id     = aws_secretsmanager_secret.pepper.id
  secret_string = var.hmac_pepper
}
