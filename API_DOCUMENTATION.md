# KD-Code System API Documentation

## Overview

The KD-Code System provides a comprehensive REST API for generating, scanning, and managing KD-Codes. All API endpoints return JSON responses and follow standard HTTP status codes.

## Base URL

```
http://localhost:5000
```

## Authentication

Some endpoints require authentication using JWT tokens. To obtain a token, use the `/auth/login` endpoint.

### Login

```
POST /auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "status": "success"
}
```

Include the token in the Authorization header for protected endpoints:
```
Authorization: Bearer <access_token>
```

## Rate Limiting

Most endpoints are rate-limited to prevent abuse:
- Generation endpoints: 30 requests per minute
- Scanning endpoints: 60 requests per minute
- Batch operations: 10 requests per minute
- Bulk operations: 5 requests per minute

## Endpoints

### Generate KD-Code

Generate a KD-Code from text/URL.

```
POST /api/generate
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body:**
```json
{
  "text": "string to encode",
  "segments_per_ring": 16,
  "anchor_radius": 10,
  "ring_width": 15,
  "scale_factor": 5,
  "max_chars": 128,
  "compression_quality": 95,
  "foreground_color": "black",
  "background_color": "white",
  "theme": null
}
```

**Parameters:**
- `text` (required): The text or URL to encode in the KD-Code
- `segments_per_ring` (optional): Number of segments per ring (8, 16, or 32). Default: 16
- `anchor_radius` (optional): Radius of the central anchor circle in pixels. Default: 10
- `ring_width` (optional): Width of each data ring in pixels. Default: 15
- `scale_factor` (optional): Scaling factor for the image (to improve quality). Default: 5
- `max_chars` (optional): Maximum number of characters allowed. Default: 128
- `compression_quality` (optional): JPEG compression quality (1-100). Default: 95
- `foreground_color` (optional): Color of the foreground elements. Default: "black"
- `background_color` (optional): Color of the background. Default: "white"
- `theme` (optional): Predefined theme for styling. Default: null

**Response:**
```json
{
  "image": "base64_encoded_png",
  "status": "success"
}
```

### Scan KD-Code

Scan and decode a KD-Code from an image.

```
POST /api/scan
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body (JSON):**
```json
{
  "image": "base64_encoded_image_with_or_without_data_url_prefix",
  "segments_per_ring": 16,
  "min_anchor_radius": 5,
  "max_anchor_radius": 100,
  "enable_multithreading": false
}
```

**Or Form Data:**
- `frame`: Image file
- `segments_per_ring` (optional): Expected number of segments per ring
- `min_anchor_radius` (optional): Minimum expected anchor radius
- `max_anchor_radius` (optional): Maximum expected anchor radius

**Parameters:**
- `image` (required): Base64-encoded image data (with or without data URL prefix)
- `segments_per_ring` (optional): Expected number of segments per ring. Default: 16
- `min_anchor_radius` (optional): Minimum expected anchor radius for filtering. Default: 5
- `max_anchor_radius` (optional): Maximum expected anchor radius for filtering. Default: 100
- `enable_multithreading` (optional): Enable multithreading for faster scanning. Default: false

**Response:**
```json
{
  "data": "decoded_text",
  "status": "success"
}
```

### Batch Generate KD-Codes

Generate multiple KD-Codes in a single request with pagination support.

```
POST /api/batch-generate
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body:**
```json
{
  "texts": ["text1", "text2", "..."],
  "page": 1,
  "page_size": 10,
  "segments_per_ring": 16,
  "anchor_radius": 10,
  "ring_width": 15,
  "scale_factor": 5,
  "max_chars": 128,
  "compression_quality": 95,
  "foreground_color": "black",
  "background_color": "white",
  "theme": null
}
```

**Parameters:**
- `texts` (required): Array of texts to encode (max 1000 items)
- `page` (optional): Page number for pagination. Default: 1
- `page_size` (optional): Number of items per page (1-100). Default: 10
- Other parameters are the same as in the generate endpoint

**Response:**
```json
{
  "results": [
    {
      "text": "original text",
      "image": "base64_encoded_png",
      "status": "success"
    }
  ],
  "total_count": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10,
  "status": "success"
}
```

### Generate QR Code

Generate a traditional QR code as an alternative to KD-Code.

```
POST /api/generate-qr
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body:**
```json
{
  "text": "string to encode",
  "box_size": 10,
  "border": 4
}
```

**Parameters:**
- `text` (required): The text or URL to encode in the QR code
- `box_size` (optional): Size of each box in pixels. Default: 10
- `border` (optional): Border size in boxes. Default: 4

**Response:**
```json
{
  "image": "base64_encoded_png",
  "type": "qr",
  "status": "success"
}
```

### Encrypt and Generate KD-Code

Encrypt sensitive data and generate a KD-Code containing the encrypted data.

```
POST /api/encrypt-and-generate
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body:**
```json
{
  "text": "sensitive text to encrypt",
  "segments_per_ring": 16,
  "anchor_radius": 10,
  "ring_width": 15,
  "scale_factor": 5,
  "max_chars": 128,
  "compression_quality": 95,
  "foreground_color": "black",
  "background_color": "white",
  "theme": null
}
```

**Response:**
```json
{
  "image": "base64_encoded_png",
  "encrypted_text": "encrypted_base64_string",
  "status": "success"
}
```

### Bulk Generate KD-Codes

Generate KD-Codes from bulk input in JSON or CSV format.

```
POST /api/bulk-generate
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token> (optional)
```

**Request Body (JSON format):**
```json
{
  "format": "json",
  "content": [
    {"text": "first text"},
    {"text": "second text"}
  ],
  "output_format": "json",
  "segments_per_ring": 16,
  "anchor_radius": 10,
  "ring_width": 15,
  "scale_factor": 5,
  "max_chars": 128,
  "compression_quality": 95,
  "foreground_color": "black",
  "background_color": "white",
  "theme": null
}
```

**Request Body (CSV format):**
```json
{
  "format": "csv",
  "csv_content": "text\nfirst text\nsecond text",
  "text_column": "text",
  "output_format": "json",
  "segments_per_ring": 16,
  "anchor_radius": 10,
  "ring_width": 15,
  "scale_factor": 5,
  "max_chars": 128,
  "compression_quality": 95,
  "foreground_color": "black",
  "background_color": "white",
  "theme": null
}
```

**Response:**
```json
{
  "content": [
    {
      "original_text": "first text",
      "encoded_image": "base64_encoded_png",
      "status": "success"
    }
  ],
  "filename": "bulk_output.json",
  "format": "json",
  "status": "success"
}
```

## Backup and Recovery Endpoints

### Create Backup

Create a system backup of configurations and generated codes.

```
POST /api/backup/create
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "backup_name",
  "include_configs": true,
  "include_generated_codes": true
}
```

**Response:**
```json
{
  "backup_path": "/app/backups/backup_name_20231015_123456.zip",
  "status": "success"
}
```

### List Backups

Get a list of all available backups.

```
GET /api/backup/list
```

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "backups": [
    {
      "name": "backup_name_20231015_123456",
      "path": "/app/backups/backup_name_20231015_123456.zip",
      "size": 1024000,
      "created_at": "2023-10-15T12:34:56Z"
    }
  ],
  "count": 1,
  "status": "success"
}
```

### Get Backup Info

Get detailed information about a specific backup.

```
GET /api/backup/info/{backup_path}
```

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "name": "backup_name_20231015_123456",
  "path": "/app/backups/backup_name_20231015_123456.zip",
  "size": 1024000,
  "created_at": "2023-10-15T12:34:56Z",
  "files": [
    "configs.json",
    "generated_codes/"
  ],
  "status": "success"
}
```

### Restore Backup

Restore the system from a backup.

```
POST /api/backup/restore
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "backup_path": "/app/backups/backup_name_20231015_123456.zip",
  "restore_configs": true,
  "restore_generated_codes": true
}
```

**Response:**
```json
{
  "message": "Backup restored successfully",
  "restored_files": 10,
  "status": "success"
}
```

## Analytics Endpoints

### Analytics Dashboard

Get overall system analytics and usage statistics.

```
GET /analytics/dashboard
```

**Headers:**
```
Authorization: Bearer <token> (optional)
```

**Response:**
```json
{
  "status": "success",
  "dashboard_data": {
    "total_codes_generated": 1250,
    "total_codes_scanned": 890,
    "active_users_today": 45,
    "generation_trends": {
      "last_7_days": [
        {"date": "2023-10-09", "count": 120},
        {"date": "2023-10-10", "count": 150},
        // ...
      ]
    }
  }
}
```

### Scan Success Rates

Get scan success/failure rate analytics.

```
GET /analytics/scan-rates
```

**Headers:**
```
Authorization: Bearer <token> (optional)
```

**Response:**
```json
{
  "status": "success",
  "scan_success_data": {
    "success_rate": 0.92,
    "failure_rate": 0.08,
    "total_scans": 1000,
    "successful_scans": 920,
    "failed_scans": 80
  }
}
```

### Performance Metrics

Get system performance metrics.

```
GET /analytics/performance
```

**Headers:**
```
Authorization: Bearer <token> (optional)
```

**Response:**
```json
{
  "status": "success",
  "performance_data": {
    "avg_generation_time_ms": 120,
    "avg_scan_time_ms": 250,
    "memory_usage_mb": 128.5,
    "cpu_usage_percent": 15.2
  }
}
```

### Usage Report

Generate a usage report for a specific date range.

```
GET /analytics/report?start_date=2023-10-01&end_date=2023-10-31
```

**Headers:**
```
Authorization: Bearer <token> (optional)
```

**Response:**
```json
{
  "status": "success",
  "report": {
    "period": {
      "start_date": "2023-10-01",
      "end_date": "2023-10-31"
    },
    "total_codes_generated": 2500,
    "total_codes_scanned": 1800,
    "top_used_texts": [
      {"text": "https://example.com", "count": 120},
      {"text": "Welcome to KD-Code", "count": 89}
    ],
    "daily_breakdown": [
      {"date": "2023-10-01", "generated": 80, "scanned": 65},
      // ...
    ]
  }
}
```

## Health and Monitoring Endpoints

### Health Check

Check the overall health of the system.

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "KD-Code System",
  "version": "1.0.0",
  "checks": {
    "database": "not_implemented",
    "redis": "not_implemented",
    "disk_space": "ok"
  }
}
```

### Readiness Check

Check if the service is ready to accept traffic.

```
GET /health/ready
```

**Response:**
```json
{
  "status": "ready"
}
```

### Metrics Endpoint

Get metrics in Prometheus format for monitoring.

```
GET /metrics
```

**Response:**
```
# HELP kdcode_requests_total Total number of requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {method="GET",endpoint="/"} 100

# HELP kdcode_requests_total Total number of generate requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {method="POST",endpoint="/api/generate"} 50

# HELP kdcode_requests_total Total number of scan requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {method="POST",endpoint="/api/scan"} 30

# HELP kdcode_active_users Current number of active users
# TYPE kdcode_active_users gauge
kdcode_active_users 5

# HELP kdcode_processing_duration_seconds Duration of processing in seconds
# TYPE kdcode_processing_duration_seconds histogram
kdcode_processing_duration_seconds_bucket{le="0.1"} 80
kdcode_processing_duration_seconds_bucket{le="0.5"} 95
kdcode_processing_duration_seconds_bucket{le="1.0"} 99
kdcode_processing_duration_seconds_bucket{le="+Inf"} 100
kdcode_processing_duration_seconds_sum 45.2
kdcode_processing_duration_seconds_count 100

# HELP kdcode_up Whether the service is up
# TYPE kdcode_up gauge
kdcode_up 1

# HELP kdcode_version Version information
# TYPE kdcode_version gauge
kdcode_version{version="1.0.0",build_date="2023-10-15"}
```

## Error Handling

The API uses standard HTTP status codes:

- `200`: Success
- `400`: Bad Request - Invalid input parameters
- `401`: Unauthorized - Authentication required
- `404`: Not Found - Requested resource not found
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Unexpected server error

Error responses follow this format:
```json
{
  "error": "Descriptive error message"
}
```

## CORS Policy

The API supports Cross-Origin Resource Sharing (CORS) for web applications hosted on different domains.