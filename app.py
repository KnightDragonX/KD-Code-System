from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import base64
import os
import hashlib
import json
from kd_core.encoder import generate_kd_code
from kd_core.decoder import decode_kd_code
from kd_core.batch_operations import batch_processor
from kd_core.bulk_operations import bulk_processor
from kd_core.qr_compatibility import generate_qr_code, is_qr_compatible
from kd_core.data_encryption import encrypt_sensitive_text, decrypt_sensitive_text
from kd_core.backup_recovery import backup_system
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS, DEFAULT_SCAN_SEGMENTS_PER_RING,
    DEFAULT_MIN_ANCHOR_RADIUS, DEFAULT_MAX_ANCHOR_RADIUS
)

def create_app():
    app = Flask(__name__)
    
    # Configure JWT
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # 1 hour
    jwt = JWTManager(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Configure caching
    cache_config = {
        'CACHE_TYPE': 'simple',  # Use simple cache for now, can be changed to redis
        'CACHE_DEFAULT_TIMEOUT': 300
    }
    app.config.from_mapping(cache_config)
    cache = Cache(app)
    
    # Apply security configurations
    from kd_core.security_config import configure_security
    app = configure_security(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/generate', methods=['POST'])
    @limiter.limit("30 per minute")
    @jwt_required(optional=True)  # Optional authentication
    def api_generate():
        try:
            # Validate request content type
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400

            data = request.get_json()

            # Validate required fields
            if not data:
                return jsonify({'error': 'Request body is required'}), 400

            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'Text input is required'}), 400

            # Extract and validate optional parameters for KD-Code generation
            try:
                segments_per_ring = int(data.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING))
                anchor_radius = int(data.get('anchor_radius', DEFAULT_ANCHOR_RADIUS))
                ring_width = int(data.get('ring_width', DEFAULT_RING_WIDTH))
                scale_factor = int(data.get('scale_factor', DEFAULT_SCALE_FACTOR))
                max_chars = int(data.get('max_chars', DEFAULT_MAX_CHARS))
                compression_quality = int(data.get('compression_quality', 95))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid parameter types. All parameters must be integers.'}), 400

            # Extract styling parameters
            foreground_color = data.get('foreground_color', 'black')
            background_color = data.get('background_color', 'white')
            theme = data.get('theme', None)

            # Create cache key based on all parameters
            cache_key = f"kdcode:{hashlib.md5((text + str(segments_per_ring) + str(anchor_radius) + str(ring_width) + str(scale_factor) + str(compression_quality) + str(foreground_color) + str(background_color) + str(theme or '')).encode()).hexdigest()}"

            # Check if result is already cached
            cached_result = cache.get(cache_key)
            if cached_result:
                app.logger.info(f"Cache hit for text: {text[:20]}...")
                return jsonify(cached_result)

            # Generate KD-Code image with parameters
            image_base64 = generate_kd_code(
                text,
                segments_per_ring=segments_per_ring,
                anchor_radius=anchor_radius,
                ring_width=ring_width,
                scale_factor=scale_factor,
                max_chars=max_chars,
                compression_quality=compression_quality,
                foreground_color=foreground_color,
                background_color=background_color,
                theme=theme
            )

            # Prepare response
            response_data = {
                'image': image_base64,
                'status': 'success'
            }

            # Cache the result for 5 minutes
            cache.set(cache_key, response_data, timeout=300)
            app.logger.info(f"Cached new KD-Code for text: {text[:20]}...")

            return jsonify(response_data)
        except ValueError as ve:
            return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
        except TypeError as te:
            return jsonify({'error': f'Type error: {str(te)}'}), 400
        except Exception as e:
            app.logger.error(f"Error in api_generate: {str(e)}")
            return jsonify({'error': 'Internal server error during generation'}), 500

    @app.route('/api/scan', methods=['POST'])
    @limiter.limit("60 per minute")
    @jwt_required(optional=True)  # Optional authentication
    def api_scan():
        try:
            image_bytes = None
            segments_per_ring = DEFAULT_SCAN_SEGMENTS_PER_RING
            min_anchor_radius = DEFAULT_MIN_ANCHOR_RADIUS
            max_anchor_radius = DEFAULT_MAX_ANCHOR_RADIUS
            
            # Check if request contains form data or JSON
            if request.is_json:
                data = request.get_json()
                
                if not data:
                    return jsonify({'error': 'Request body is required'}), 400
                
                image_data = data.get('image', '')
                if not image_data:
                    return jsonify({'error': 'Image data is required'}), 400

                # Decode base64 image
                # Handle both cases: with and without data URL prefix
                try:
                    if image_data.startswith('data:image'):
                        header, encoded = image_data.split(',', 1)
                        image_bytes = base64.b64decode(encoded)
                    else:
                        # If it's just the base64 string without header
                        image_bytes = base64.b64decode(image_data)
                except Exception:
                    return jsonify({'error': 'Invalid base64 image data'}), 400
                
                # Extract optional parameters for KD-Code scanning
                try:
                    segments_per_ring = int(data.get('segments_per_ring', DEFAULT_SCAN_SEGMENTS_PER_RING))
                    min_anchor_radius = int(data.get('min_anchor_radius', DEFAULT_MIN_ANCHOR_RADIUS))
                    max_anchor_radius = int(data.get('max_anchor_radius', DEFAULT_MAX_ANCHOR_RADIUS))
                    enable_multithreading = bool(data.get('enable_multithreading', False))
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid parameter types. All parameters must be integers.'}), 400
            else:
                # Handle file upload
                if 'frame' not in request.files:
                    return jsonify({'error': 'Image file is required'}), 400

                file = request.files['frame']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400

                try:
                    image_bytes = file.read()
                except Exception:
                    return jsonify({'error': 'Error reading uploaded file'}), 400
                
                # Extract optional parameters from form data if available
                try:
                    segments_per_ring = int(request.form.get('segments_per_ring', DEFAULT_SCAN_SEGMENTS_PER_RING))
                    min_anchor_radius = int(request.form.get('min_anchor_radius', DEFAULT_MIN_ANCHOR_RADIUS))
                    max_anchor_radius = int(request.form.get('max_anchor_radius', DEFAULT_MAX_ANCHOR_RADIUS))
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid parameter types. All parameters must be integers.'}), 400

            # Decode KD-Code with parameters
            decoded_text = decode_kd_code(
                image_bytes,
                segments_per_ring=segments_per_ring,
                min_anchor_radius=min_anchor_radius,
                max_anchor_radius=max_anchor_radius,
                enable_multithreading=enable_multithreading
            )

            if decoded_text is None:
                return jsonify({'error': 'No KD-Code detected in image'}), 400

            return jsonify({
                'data': decoded_text,
                'status': 'success'
            })
        except ValueError as ve:
            return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
        except TypeError as te:
            return jsonify({'error': f'Type error: {str(te)}'}), 400
        except Exception as e:
            app.logger.error(f"Error in api_scan: {str(e)}")
            return jsonify({'error': 'Internal server error during scanning'}), 500

    @app.route('/api/batch-generate', methods=['POST'])
    @limiter.limit("10 per minute")
    @jwt_required(optional=True)  # Optional authentication
    def api_batch_generate():
        """API endpoint for batch generation of KD-Codes with pagination support"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            # Get the list of texts to encode
            texts = data.get('texts', [])
            if not texts or not isinstance(texts, list):
                return jsonify({'error': 'A list of texts is required'}), 400
            
            # Validate that we have reasonable limits
            if len(texts) > 1000:  # Prevent overly large batches
                return jsonify({'error': 'Too many texts in batch. Maximum is 1000 items.'}), 400
            
            # Get pagination parameters
            page = int(data.get('page', 1))
            page_size = int(data.get('page_size', 10))
            
            # Validate pagination parameters
            if page < 1 or page_size < 1 or page_size > 100:
                return jsonify({'error': 'Invalid pagination parameters. Page and page_size must be positive integers, page_size max 100.'}), 400
            
            # Extract other optional parameters for KD-Code generation
            try:
                segments_per_ring = int(data.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING))
                anchor_radius = int(data.get('anchor_radius', DEFAULT_ANCHOR_RADIUS))
                ring_width = int(data.get('ring_width', DEFAULT_RING_WIDTH))
                scale_factor = int(data.get('scale_factor', DEFAULT_SCALE_FACTOR))
                max_chars = int(data.get('max_chars', DEFAULT_MAX_CHARS))
                compression_quality = int(data.get('compression_quality', 95))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid parameter types. All parameters must be integers.'}), 400
            
            # Extract styling parameters
            foreground_color = data.get('foreground_color', 'black')
            background_color = data.get('background_color', 'white')
            theme = data.get('theme', None)
            
            # Perform batch generation with pagination
            results = batch_processor.generate_batch(
                texts=texts,
                page=page,
                page_size=page_size,
                segments_per_ring=segments_per_ring,
                anchor_radius=anchor_radius,
                ring_width=ring_width,
                scale_factor=scale_factor,
                max_chars=max_chars,
                compression_quality=compression_quality,
                foreground_color=foreground_color,
                background_color=background_color,
                theme=theme
            )
            
            return jsonify(results)
        except ValueError as ve:
            return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
        except Exception as e:
            app.logger.error(f"Error in api_batch_generate: {str(e)}")
            return jsonify({'error': 'Internal server error during batch generation'}), 500

    @app.route('/api/generate-qr', methods=['POST'])
    @limiter.limit("30 per minute")
    @jwt_required(optional=True)  # Optional authentication
    def api_generate_qr():
        """API endpoint for generating QR codes"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'Text input is required'}), 400
            
            # Validate QR compatibility
            if not is_qr_compatible(text):
                return jsonify({'error': 'Text is not compatible with QR code standards'}), 400
            
            # Extract optional parameters for QR code generation
            try:
                box_size = int(data.get('box_size', 10))
                border = int(data.get('border', 4))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid parameter types. box_size and border must be integers.'}), 400
            
            # Generate QR code
            qr_code_b64 = generate_qr_code(text, box_size=box_size, border=border)
            
            return jsonify({
                'image': qr_code_b64,
                'type': 'qr',
                'status': 'success'
            })
        except ImportError as e:
            return jsonify({'error': f'Dependency not available: {str(e)}'}), 500
        except Exception as e:
            app.logger.error(f"Error in api_generate_qr: {str(e)}")
            return jsonify({'error': 'Internal server error during QR code generation'}), 500

    @app.route('/auth/login', methods=['POST'])
    def login():
        """Authentication endpoint for enterprise users"""
        try:
            data = request.get_json()
            username = data.get('username', '')
            password = data.get('password', '')
            
            # In a real application, you would validate credentials against a database
            # For demo purposes, we'll use hardcoded credentials
            if username == 'admin' and password == 'secure_password':
                access_token = create_access_token(identity=username)
                return jsonify({
                    'access_token': access_token,
                    'status': 'success'
                })
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
        except Exception as e:
            return jsonify({'error': 'Login failed'}), 500

    @app.route('/api/encrypt-and-generate', methods=['POST'])
    @limiter.limit("30 per minute")
    @jwt_required(optional=True)  # Optional authentication
    def api_encrypt_and_generate():
        """API endpoint for encrypting sensitive data and generating KD-Code"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'Text input is required'}), 400
            
            # Encrypt the sensitive text
            encrypted_text = encrypt_sensitive_text(text)
            
            # Generate KD-Code with the encrypted text
            # Extract and validate optional parameters for KD-Code generation
            try:
                segments_per_ring = int(data.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING))
                anchor_radius = int(data.get('anchor_radius', DEFAULT_ANCHOR_RADIUS))
                ring_width = int(data.get('ring_width', DEFAULT_RING_WIDTH))
                scale_factor = int(data.get('scale_factor', DEFAULT_SCALE_FACTOR))
                max_chars = int(data.get('max_chars', DEFAULT_MAX_CHARS))
                compression_quality = int(data.get('compression_quality', 95))
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid parameter types. All parameters must be integers.'}), 400

            # Extract styling parameters
            foreground_color = data.get('foreground_color', 'black')
            background_color = data.get('background_color', 'white')
            theme = data.get('theme', None)

            # Create cache key based on all parameters
            cache_key = f"kdcode:{hashlib.md5((encrypted_text + str(segments_per_ring) + str(anchor_radius) + str(ring_width) + str(scale_factor) + str(compression_quality) + str(foreground_color) + str(background_color) + str(theme or '')).encode()).hexdigest()}"

            # Check if result is already cached
            cached_result = cache.get(cache_key)
            if cached_result:
                app.logger.info(f"Cache hit for encrypted text")
                return jsonify(cached_result)

            # Generate KD-Code image with encrypted text
            image_base64 = generate_kd_code(
                encrypted_text,
                segments_per_ring=segments_per_ring,
                anchor_radius=anchor_radius,
                ring_width=ring_width,
                scale_factor=scale_factor,
                max_chars=max_chars,
                compression_quality=compression_quality,
                foreground_color=foreground_color,
                background_color=background_color,
                theme=theme
            )

            # Prepare response
            response_data = {
                'image': image_base64,
                'encrypted_text': encrypted_text,  # Include encrypted text in response
                'status': 'success'
            }

            # Cache the result for 5 minutes
            cache.set(cache_key, response_data, timeout=300)
            app.logger.info("Cached new encrypted KD-Code")

            return jsonify(response_data)
        except Exception as e:
            app.logger.error(f"Error in api_encrypt_and_generate: {str(e)}")
            return jsonify({'error': 'Internal server error during encrypted generation'}), 500

    @app.route('/api/backup/create', methods=['POST'])
    @jwt_required()
    def api_create_backup():
        """API endpoint for creating system backups"""
        try:
            data = request.get_json()
            
            backup_name = data.get('name') if data else None
            include_configs = data.get('include_configs', True) if data else True
            include_generated_codes = data.get('include_generated_codes', True) if data else True
            
            backup_path = backup_system.create_backup(
                backup_name=backup_name,
                include_configs=include_configs,
                include_generated_codes=include_generated_codes
            )
            
            return jsonify({
                'backup_path': backup_path,
                'status': 'success'
            })
        except Exception as e:
            app.logger.error(f"Error in api_create_backup: {str(e)}")
            return jsonify({'error': 'Internal server error during backup creation'}), 500

    @app.route('/api/backup/list', methods=['GET'])
    @jwt_required()
    def api_list_backups():
        """API endpoint for listing available backups"""
        try:
            backups = backup_system.list_backups()
            
            return jsonify({
                'backups': backups,
                'count': len(backups),
                'status': 'success'
            })
        except Exception as e:
            app.logger.error(f"Error in api_list_backups: {str(e)}")
            return jsonify({'error': 'Internal server error during backup listing'}), 500

    @app.route('/api/backup/info/<path:backup_path>', methods=['GET'])
    @jwt_required()
    def api_backup_info(backup_path):
        """API endpoint for getting backup information"""
        try:
            info = backup_system.get_backup_info(backup_path)
            
            if 'error' in info:
                return jsonify(info), 400
            
            return jsonify(info)
        except Exception as e:
            app.logger.error(f"Error in api_backup_info: {str(e)}")
            return jsonify({'error': 'Internal server error during backup info retrieval'}), 500

    @app.route('/api/backup/restore', methods=['POST'])
    @jwt_required()
    def api_restore_backup():
        """API endpoint for restoring from a backup"""
        try:
            data = request.get_json()
            
            if not data or 'backup_path' not in data:
                return jsonify({'error': 'Backup path is required'}), 400
            
            backup_path = data['backup_path']
            restore_configs = data.get('restore_configs', True)
            restore_generated_codes = data.get('restore_generated_codes', True)
            
            result = backup_system.restore_backup(
                backup_path=backup_path,
                restore_configs=restore_configs,
                restore_generated_codes=restore_generated_codes
            )
            
            if not result['success']:
                status_code = 400 if 'error' in result else 500
                return jsonify(result), status_code
            
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in api_restore_backup: {str(e)}")
            return jsonify({'error': 'Internal server error during backup restoration'}), 500

    @app.route('/api/bulk-generate', methods=['POST'])
    @limiter.limit("5 per minute")
    @jwt_required(optional=True)  # Optional authentication for this endpoint
    def api_bulk_generate():
        """API endpoint for bulk generation of KD-Codes from various input formats"""
        try:
            # Check if request contains form data or JSON
            if request.is_json:
                data = request.get_json()
                
                if not data:
                    return jsonify({'error': 'Request body is required'}), 400
                
                # Get input format and content
                input_format = data.get('format', 'json')  # 'json', 'csv'
                content = data.get('content', [])
                
                # Extract texts based on format
                if input_format == 'json':
                    texts = bulk_processor.import_from_json(content)
                elif input_format == 'csv':
                    csv_content = data.get('csv_content', '')
                    text_column = data.get('text_column', 'text')
                    texts = bulk_processor.import_from_csv(csv_content, text_column)
                else:
                    return jsonify({'error': 'Unsupported input format. Use "json" or "csv".'}), 400
            else:
                # Handle file uploads
                if 'file' not in request.files:
                    return jsonify({'error': 'File is required for bulk operations'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Read file content
                content = file.read().decode('utf-8')
                input_format = file.filename.split('.')[-1].lower()
                
                # Extract texts based on format
                if input_format == 'json':
                    texts = bulk_processor.import_from_json(content)
                elif input_format == 'csv':
                    text_column = request.form.get('text_column', 'text')
                    texts = bulk_processor.import_from_csv(content, text_column)
                else:
                    return jsonify({'error': f'Unsupported file format: {input_format}. Use CSV or JSON.'}), 400
            
            # Validate texts
            if not texts or not isinstance(texts, list):
                return jsonify({'error': 'No valid texts found in input'}), 400
            
            if len(texts) > 10000:  # Prevent overly large bulk operations
                return jsonify({'error': 'Too many texts in bulk operation. Maximum is 10,000 items.'}), 400
            
            # Extract optional parameters for KD-Code generation
            try:
                segments_per_ring = int(request.json.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING) if request.is_json else request.form.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING))
                anchor_radius = int(request.json.get('anchor_radius', DEFAULT_ANCHOR_RADIUS) if request.is_json else request.form.get('anchor_radius', DEFAULT_ANCHOR_RADIUS))
                ring_width = int(request.json.get('ring_width', DEFAULT_RING_WIDTH) if request.is_json else request.form.get('ring_width', DEFAULT_RING_WIDTH))
                scale_factor = int(request.json.get('scale_factor', DEFAULT_SCALE_FACTOR) if request.is_json else request.form.get('scale_factor', DEFAULT_SCALE_FACTOR))
                max_chars = int(request.json.get('max_chars', DEFAULT_MAX_CHARS) if request.is_json else request.form.get('max_chars', DEFAULT_MAX_CHARS))
                compression_quality = int(request.json.get('compression_quality', 95) if request.is_json else request.form.get('compression_quality', 95))
                foreground_color = request.json.get('foreground_color', 'black') if request.is_json else request.form.get('foreground_color', 'black')
                background_color = request.json.get('background_color', 'white') if request.is_json else request.form.get('background_color', 'white')
                theme = request.json.get('theme', None) if request.is_json else request.form.get('theme', None)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid parameter types.'}), 400
            
            # Process bulk generation
            results = bulk_processor.process_bulk_generation(
                texts=texts,
                segments_per_ring=segments_per_ring,
                anchor_radius=anchor_radius,
                ring_width=ring_width,
                scale_factor=scale_factor,
                max_chars=max_chars,
                compression_quality=compression_quality,
                foreground_color=foreground_color,
                background_color=background_color,
                theme=theme
            )
            
            # Determine output format
            output_format = request.json.get('output_format', 'json') if request.is_json else request.form.get('output_format', 'json')
            
            if output_format == 'csv':
                csv_content, filename = bulk_processor.export_to_csv(results)
                return jsonify({
                    'content': csv_content,
                    'filename': filename,
                    'format': 'csv',
                    'status': 'success'
                })
            else:  # Default to JSON
                json_content, filename = bulk_processor.export_to_json(results)
                return jsonify({
                    'content': results,  # Return results directly as JSON
                    'filename': filename,
                    'format': 'json',
                    'status': 'success'
                })
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format'}), 400
        except Exception as e:
            app.logger.error(f"Error in api_bulk_generate: {str(e)}")
            return jsonify({'error': 'Internal server error during bulk generation'}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        try:
            # Perform basic health checks
            # - Check if the app is running
            # - Check if dependencies are accessible (optional)
            
            health_status = {
                'status': 'healthy',
                'service': 'KD-Code System',
                'version': '1.0.0',
                'checks': {
                    'database': 'not_implemented',  # Would check DB connection if using one
                    'redis': 'not_implemented',     # Would check Redis if using it for more than caching
                    'disk_space': 'ok'              # Would check available disk space
                }
            }
            
            return jsonify(health_status), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/health/ready', methods=['GET'])
    def readiness_check():
        """Readiness check endpoint"""
        try:
            # Check if the service is ready to accept traffic
            # For now, just return healthy, but in a real app you might check:
            # - Database connections
            # - External service dependencies
            # - Resource availability
            
            return jsonify({'status': 'ready'}), 200
        except Exception as e:
            return jsonify({'status': 'not_ready', 'error': str(e)}), 500

    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Metrics endpoint for Prometheus monitoring"""
        # In a real application, you would collect actual metrics
        # For now, we'll return dummy metrics in Prometheus format
        
        from datetime import datetime
        metrics_text = f"""# HELP kdcode_requests_total Total number of requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {{method="GET",endpoint="/"}} 100

# HELP kdcode_requests_total Total number of generate requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {{method="POST",endpoint="/api/generate"}} 50

# HELP kdcode_requests_total Total number of scan requests
# TYPE kdcode_requests_total counter
kdcode_requests_total {{method="POST",endpoint="/api/scan"}} 30

# HELP kdcode_active_users Current number of active users
# TYPE kdcode_active_users gauge
kdcode_active_users 5

# HELP kdcode_processing_duration_seconds Duration of processing in seconds
# TYPE kdcode_processing_duration_seconds histogram
kdcode_processing_duration_seconds_bucket{{le="0.1"}} 80
kdcode_processing_duration_seconds_bucket{{le="0.5"}} 95
kdcode_processing_duration_seconds_bucket{{le="1.0"}} 99
kdcode_processing_duration_seconds_bucket{{le="+Inf"}} 100
kdcode_processing_duration_seconds_sum 45.2
kdcode_processing_duration_seconds_count 100

# HELP kdcode_up Whether the service is up
# TYPE kdcode_up gauge
kdcode_up 1

# HELP kdcode_version Version information
# TYPE kdcode_version gauge
kdcode_version{{version="1.0.0",build_date="{datetime.now().strftime('%Y-%m-%d')}"}}

"""
        return metrics_text, 200, {'Content-Type': 'text/plain; version=0.0.4'}

    @app.route('/analytics/dashboard', methods=['GET'])
    def analytics_dashboard():
        """Dashboard endpoint for usage analytics"""
        try:
            from kd_core.analytics import get_analytics_dashboard
            dashboard_data = get_analytics_dashboard()
            
            return jsonify({
                'status': 'success',
                'dashboard_data': dashboard_data
            })
        except Exception as e:
            app.logger.error(f"Error in analytics_dashboard: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve analytics data'
            }), 500

    @app.route('/analytics/scan-rates', methods=['GET'])
    def scan_success_rates():
        """Endpoint for scan success/failure rate analytics"""
        try:
            from kd_core.analytics import analytics
            scan_rates_data = analytics.get_scan_success_rates()
            
            return jsonify({
                'status': 'success',
                'scan_success_data': scan_rates_data
            })
        except Exception as e:
            app.logger.error(f"Error in scan_success_rates: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve scan success/failure data'
            }), 500

    @app.route('/analytics/performance', methods=['GET'])
    def performance_metrics():
        """Endpoint for performance metrics"""
        try:
            from kd_core.analytics import get_performance_metrics
            perf_data = get_performance_metrics()
            
            return jsonify({
                'status': 'success',
                'performance_data': perf_data
            })
        except Exception as e:
            app.logger.error(f"Error in performance_metrics: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve performance metrics'
            }), 500

    @app.route('/analytics/report', methods=['GET'])
    def usage_report():
        """Endpoint for generating usage reports"""
        try:
            from kd_core.analytics import generate_usage_report
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            report_data = generate_usage_report(start_date=start_date, end_date=end_date)
            
            return jsonify({
                'status': 'success',
                'report': report_data
            })
        except Exception as e:
            app.logger.error(f"Error in usage_report: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate usage report'
            }), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)