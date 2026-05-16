resource "aws_ecs_cluster" "main" {
  name = "membramoney-cluster"
  tags = local.tags
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "membramoney-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "membramoney/backend:latest"
    essential = true
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "ENV", value = var.environment },
      { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/membramoney" }
    ]
    secrets = [
      { name = "JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt.arn },
      { name = "HMAC_PEPPER", valueFrom = aws_secretsmanager_secret.pepper.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "backend"
      }
    }
  }])

  tags = local.tags
}

resource "aws_ecs_service" "backend" {
  name            = "membramoney-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/membramoney-backend"
  retention_in_days = 7
  tags              = local.tags
}

resource "aws_security_group" "ecs" {
  name_prefix = "membramoney-ecs-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}
