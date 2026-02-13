# KD-Code System Deployment Guide

## Overview

This document provides detailed instructions for deploying the KD-Code System in various environments, from local development to production clusters. The system is designed to be deployed using containerization technologies for consistency and scalability.

## Prerequisites

Before deploying the KD-Code System, ensure your environment meets the following requirements:

### System Requirements
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher (or standalone docker-compose)
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: Minimum 2GB free space
- **Ports**: Availability of ports 80, 443, and 5000

### Software Dependencies
- Git
- OpenSSL (for generating secrets)
- curl (for health checks)
- bash-compatible shell

## Quick Deployment

For a quick local deployment:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/KD-Code-System.git
   cd KD-Code-System
   ```

2. Make the deployment script executable:
   ```bash
   chmod +x deploy.sh
   ```

3. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

4. Access the application at `http://localhost:5000`

## Production Deployment

### Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Application Configuration
FLASK_ENV=production
FLASK_DEBUG=False

# Optional: Database configuration if using persistence
DATABASE_URL=postgresql://user:password@db:5432/kdcode

# Optional: Cloud storage for backups
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET_NAME=
```

### Docker Compose Deployment

The system uses Docker Compose to orchestrate multiple services:

#### Services Included
- **kd-code-web**: Main Flask application
- **redis**: Caching and session storage
- **nginx**: Reverse proxy and SSL termination

#### Deployment Steps

1. Ensure Docker and Docker Compose are installed
2. Navigate to the project directory
3. Create the `.env` file with appropriate values
4. Run the deployment:

   ```bash
   docker-compose down --remove-orphans  # Stop any existing containers
   docker-compose build                  # Build fresh images
   docker-compose up -d                  # Start services in detached mode
   ```

5. Verify the deployment:
   ```bash
   docker-compose ps                     # Check service status
   docker-compose logs kd-code-web       # Check application logs
   curl http://localhost:5000/health     # Health check
   ```

### Kubernetes Deployment

For Kubernetes deployments, use the provided manifests or Helm chart:

1. Install Helm if not already present:
   ```bash
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   ```

2. Add the KD-Code System Helm repository:
   ```bash
   helm repo add kd-code-system https://your-repo.github.io/kd-code-system
   helm repo update
   ```

3. Deploy with default values:
   ```bash
   helm install kd-code-release kd-code-system/kd-code-system
   ```

4. Or deploy with custom values:
   ```bash
   helm install kd-code-release kd-code-system/kd-code-system -f values.yaml
   ```

### Manual Deployment

For manual deployments without containers:

1. Install Python 3.9+ and pip
2. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-dev python3-pip libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
   ```

3. Install Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables:
   ```bash
   export JWT_SECRET_KEY=your-secret-key
   export REDIS_URL=redis://localhost:6379/0
   ```

5. Run the application:
   ```bash
   python app.py
   ```

## Configuration Options

### Application Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `JWT_SECRET_KEY` | Secret key for JWT token signing | Required |
| `FLASK_ENV` | Environment mode (development/production) | production |
| `REDIS_URL` | Redis connection URL | redis://redis:6379/0 |
| `DATABASE_URL` | Database connection URL | None |
| `MAX_CONTENT_LENGTH` | Maximum upload size in MB | 16 |

### KD-Code Generation Parameters

These can be configured via environment variables or API parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `DEFAULT_SEGMENTS_PER_RING` | Segments per ring | 16 |
| `DEFAULT_ANCHOR_RADIUS` | Anchor circle radius | 10 |
| `DEFAULT_RING_WIDTH` | Width of data rings | 15 |
| `DEFAULT_SCALE_FACTOR` | Image scaling factor | 5 |
| `DEFAULT_MAX_CHARS` | Maximum characters | 128 |

## SSL/TLS Configuration

The system uses Nginx as a reverse proxy for SSL termination:

1. Place SSL certificates in the `ssl/` directory:
   - `ssl/cert.pem` - Certificate file
   - `ssl/key.pem` - Private key file

2. Update `nginx.conf` to reference your certificates:
   ```nginx
   ssl_certificate /etc/nginx/ssl/cert.pem;
   ssl_certificate_key /etc/nginx/ssl/key.pem;
   ```

3. Restart the services after configuration changes:
   ```bash
   docker-compose restart nginx
   ```

## Backup and Recovery

### Automated Backups

The system includes automated backup capabilities:

1. Configure backup settings in your `.env` file:
   ```bash
   BACKUP_ENABLED=true
   BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
   BACKUP_RETENTION_DAYS=30
   ```

2. Backups are stored in the `./backups` directory (mounted as volume)

### Manual Backups

Create manual backups using the API:

```bash
curl -X POST http://localhost:5000/api/backup/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "manual-backup-$(date +%Y%m%d)", "include_configs": true, "include_generated_codes": true}'
```

### Restoring from Backup

1. List available backups:
   ```bash
   curl -X GET http://localhost:5000/api/backup/list \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

2. Restore from a specific backup:
   ```bash
   curl -X POST http://localhost:5000/api/backup/restore \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"backup_path": "/app/backups/backup-name.zip", "restore_configs": true, "restore_generated_codes": true}'
   ```

## Monitoring and Logging

### Health Checks

The system provides multiple health check endpoints:

- `/health` - General health status
- `/health/ready` - Readiness for traffic
- `/metrics` - Prometheus-compatible metrics

### Log Management

Logs are managed differently based on deployment method:

#### Docker Compose
```bash
# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs kd-code-web

# Follow logs in real-time
docker-compose logs -f kd-code-web
```

#### Kubernetes
```bash
# View pod logs
kubectl logs deployment/kd-code-web

# Follow logs in real-time
kubectl logs -f deployment/kd-code-web
```

### Metrics Collection

The system exposes metrics in Prometheus format at `/metrics`. Configure your Prometheus instance to scrape this endpoint.

## Scaling

### Horizontal Scaling

To scale the web service:

#### Docker Compose
```bash
# Scale to 3 instances
docker-compose up -d --scale kd-code-web=3
```

#### Kubernetes
```bash
# Scale deployment to 3 replicas
kubectl scale deployment kd-code-web --replicas=3
```

### Vertical Scaling

Increase resources allocated to containers:

#### Docker Compose
Modify the `docker-compose.yml`:
```yaml
services:
  kd-code-web:
    # ... other config
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

#### Kubernetes
Modify resource requests and limits in the deployment manifest:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "4Gi"
    cpu: "2"
```

## Security Best Practices

### Secrets Management

Never hardcode secrets in configuration files:
- Use environment variables for secrets
- Consider using a secrets manager (HashiCorp Vault, AWS Secrets Manager)
- Rotate secrets regularly

### Network Security

- Restrict network access to necessary ports only
- Use SSL/TLS for all external communications
- Implement rate limiting to prevent abuse
- Use a Web Application Firewall (WAF)

### Container Security

- Keep base images updated
- Run containers as non-root user
- Scan images for vulnerabilities
- Use minimal base images

## Troubleshooting

### Common Issues

#### Service Won't Start
1. Check Docker daemon status: `sudo systemctl status docker`
2. Verify available disk space: `df -h`
3. Check logs: `docker-compose logs kd-code-web`

#### High Memory Usage
1. Check current usage: `docker stats`
2. Adjust memory limits in compose file
3. Consider scaling horizontally instead of vertically

#### Slow Response Times
1. Check system resources: `htop`
2. Verify Redis connectivity: `docker-compose exec redis ping`
3. Review application logs for errors

### Diagnostic Commands

```bash
# Check all services status
docker-compose ps

# Check resource usage
docker stats

# View application logs
docker-compose logs kd-code-web

# Test health endpoint
curl http://localhost:5000/health

# Test internal connectivity
docker-compose exec kd-code-web curl http://redis:6379/ping
```

## Updating the System

### Docker Compose Updates

1. Pull latest changes:
   ```bash
   git pull origin main
   ```

2. Rebuild and restart:
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

### Zero-Downtime Updates

For Kubernetes deployments, use rolling updates:
```bash
kubectl rollout restart deployment/kd-code-web
kubectl rollout status deployment/kd-code-web
```

## Uninstalling

### Docker Compose Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove associated volumes (deletes data!)
docker-compose down -v

# Remove images
docker rmi $(docker images "kd-code-system_*" -q)
```

### Kubernetes Cleanup

```bash
# Uninstall Helm release
helm uninstall kd-code-release

# Remove custom resources if any
kubectl delete crd kdcodeinstances.kdcode.example.com
```

## Support

For deployment assistance:
- Check the issue tracker on GitHub
- Contact the development team
- Consult the community forums
- Engage premium support for enterprise deployments