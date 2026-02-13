"""
GraphQL API v2 for KD-Code System
Provides enhanced API functionality with GraphQL support
"""

from flask import Flask, request, jsonify
import graphene
from graphene import ObjectType, String, Int, Boolean, List, Schema, Field, Argument
from graphene.types import Scalar
from flask_graphql import GraphQL
import base64
from datetime import datetime
from typing import Optional
import json

# Import core functionality
from kd_core.encoder import generate_kd_code
from kd_core.decoder import decode_kd_code
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS
)


# Define GraphQL types
class KDCodeType(ObjectType):
    """GraphQL type for KD-Code"""
    id = String(required=True)
    content = String(required=True)
    image_data = String(required=True)  # Base64 encoded image
    created_at = String(required=True)
    segments_per_ring = Int()
    anchor_radius = Int()
    ring_width = Int()
    scale_factor = Int()
    scan_count = Int()
    last_scanned = String()


class GenerateInput(graphene.InputObjectType):
    """Input type for KD-Code generation"""
    text = String(required=True)
    segments_per_ring = Int(default_value=DEFAULT_SEGMENTS_PER_RING)
    anchor_radius = Int(default_value=DEFAULT_ANCHOR_RADIUS)
    ring_width = Int(default_value=DEFAULT_RING_WIDTH)
    scale_factor = Int(default_value=DEFAULT_SCALE_FACTOR)
    max_chars = Int(default_value=DEFAULT_MAX_CHARS)
    compression_quality = Int(default_value=95)
    foreground_color = String(default_value="black")
    background_color = String(default_value="white")
    theme = String()


class ScanInput(graphene.InputObjectType):
    """Input type for KD-Code scanning"""
    image_data = String(required=True)  # Base64 encoded image
    segments_per_ring = Int(default_value=16)
    min_anchor_radius = Int(default_value=5)
    max_anchor_radius = Int(default_value=100)


class GenerateKDCodePayload(ObjectType):
    """Payload for KD-Code generation"""
    success = Boolean()
    kd_code = Field(KDCodeType)
    error = String()


class ScanKDCodePayload(ObjectType):
    """Payload for KD-Code scanning"""
    success = Boolean()
    decoded_text = String()
    error = String()


class Query(ObjectType):
    """GraphQL query definitions"""
    
    # Get a specific KD-Code by ID
    kd_code = Field(KDCodeType, id=String(required=True))
    
    # Get all KD-Codes (with pagination)
    all_kd_codes = List(KDCodeType, limit=Int(default_value=10), offset=Int(default_value=0))
    
    # Search KD-Codes
    search_kd_codes = List(KDCodeType, query=String(required=True))
    
    # Get analytics
    analytics = Field(lambda: AnalyticsType)
    
    def resolve_kd_code(self, info, id):
        """Resolve a specific KD-Code by ID"""
        # In a real implementation, this would fetch from a database
        # For now, we'll return a mock object
        return KDCodeType(
            id=id,
            content="Mock content for demonstration",
            image_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            created_at=datetime.now().isoformat(),
            segments_per_ring=16,
            anchor_radius=10,
            ring_width=15,
            scale_factor=5,
            scan_count=0,
            last_scanned=None
        )
    
    def resolve_all_kd_codes(self, info, limit=10, offset=0):
        """Resolve all KD-Codes with pagination"""
        # In a real implementation, this would fetch from a database
        # For now, we'll return mock objects
        codes = []
        for i in range(offset, offset + limit):
            codes.append(KDCodeType(
                id=f"mock_code_{i}",
                content=f"Mock content {i}",
                image_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                created_at=datetime.now().isoformat(),
                segments_per_ring=16,
                anchor_radius=10,
                ring_width=15,
                scale_factor=5,
                scan_count=0,
                last_scanned=None
            ))
        return codes
    
    def resolve_search_kd_codes(self, info, query):
        """Search KD-Codes by content"""
        # In a real implementation, this would search in a database
        # For now, we'll return mock results
        return [
            KDCodeType(
                id="search_result_1",
                content=f"Search result for: {query}",
                image_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                created_at=datetime.now().isoformat(),
                segments_per_ring=16,
                anchor_radius=10,
                ring_width=15,
                scale_factor=5,
                scan_count=0,
                last_scanned=None
            )
        ]
    
    def resolve_analytics(self, info):
        """Get analytics data"""
        return AnalyticsType(
            total_codes=150,
            total_scans=1200,
            active_users=45,
            avg_scan_time=0.8
        )


class Mutation(ObjectType):
    """GraphQL mutation definitions"""
    
    # Generate a new KD-Code
    generate_kd_code = Field(
        GenerateKDCodePayload,
        input=Argument(GenerateInput, required=True)
    )
    
    # Scan a KD-Code
    scan_kd_code = Field(
        ScanKDCodePayload,
        input=Argument(ScanInput, required=True)
    )
    
    def mutate_generate_kd_code(self, info, input):
        """Generate a new KD-Code"""
        try:
            # Generate the KD-Code using the core encoder
            image_b64 = generate_kd_code(
                text=input.text,
                segments_per_ring=input.segments_per_ring or DEFAULT_SEGMENTS_PER_RING,
                anchor_radius=input.anchor_radius or DEFAULT_ANCHOR_RADIUS,
                ring_width=input.ring_width or DEFAULT_RING_WIDTH,
                scale_factor=input.scale_factor or DEFAULT_SCALE_FACTOR,
                max_chars=input.max_chars or DEFAULT_MAX_CHARS,
                compression_quality=getattr(input, 'compression_quality', 95),
                foreground_color=getattr(input, 'foreground_color', 'black'),
                background_color=getattr(input, 'background_color', 'white'),
                theme=getattr(input, 'theme', None)
            )
            
            # Create a mock KD-Code object
            kd_code = KDCodeType(
                id=f"generated_{datetime.now().timestamp()}",
                content=input.text,
                image_data=image_b64,
                created_at=datetime.now().isoformat(),
                segments_per_ring=input.segments_per_ring,
                anchor_radius=input.anchor_radius,
                ring_width=input.ring_width,
                scale_factor=input.scale_factor,
                scan_count=0,
                last_scanned=None
            )
            
            return GenerateKDCodePayload(success=True, kd_code=kd_code, error=None)
        except Exception as e:
            return GenerateKDCodePayload(success=False, kd_code=None, error=str(e))
    
    def mutate_scan_kd_code(self, info, input):
        """Scan a KD-Code"""
        try:
            # Decode the base64 image data
            image_bytes = base64.b64decode(input.image_data)
            
            # Decode the KD-Code using the core decoder
            decoded_text = decode_kd_code(
                image_bytes,
                segments_per_ring=input.segments_per_ring,
                min_anchor_radius=getattr(input, 'min_anchor_radius', 5),
                max_anchor_radius=getattr(input, 'max_anchor_radius', 100)
            )
            
            if decoded_text is None:
                return ScanKDCodePayload(success=False, decoded_text=None, error="No KD-Code detected in image")
            
            return ScanKDCodePayload(success=True, decoded_text=decoded_text, error=None)
        except Exception as e:
            return ScanKDCodePayload(success=False, decoded_text=None, error=str(e))


class AnalyticsType(ObjectType):
    """GraphQL type for analytics data"""
    total_codes = Int()
    total_scans = Int()
    active_users = Int()
    avg_scan_time = Float()


# Create the schema
schema = Schema(query=Query, mutation=Mutation)


# Create Flask app with GraphQL endpoint
def create_graphql_app():
    """Create a Flask app with GraphQL endpoint"""
    app = Flask(__name__)
    
    # Add GraphQL endpoint
    app.add_url_rule(
        '/graphql',
        view_func=GraphQL.as_view('graphql', schema=schema, graphiql=True)  # Enable GraphiQL interface
    )
    
    # Keep the original REST API endpoints for backward compatibility
    @app.route('/api/v2/generate', methods=['POST'])
    def api_v2_generate():
        """REST API v2 endpoint for generating KD-Codes"""
        try:
            data = request.get_json()
            
            if not data or 'text' not in data:
                return jsonify({'error': 'Text is required'}), 400
            
            # Extract parameters
            text = data['text']
            segments_per_ring = data.get('segments_per_ring', DEFAULT_SEGMENTS_PER_RING)
            anchor_radius = data.get('anchor_radius', DEFAULT_ANCHOR_RADIUS)
            ring_width = data.get('ring_width', DEFAULT_RING_WIDTH)
            scale_factor = data.get('scale_factor', DEFAULT_SCALE_FACTOR)
            max_chars = data.get('max_chars', DEFAULT_MAX_CHARS)
            compression_quality = data.get('compression_quality', 95)
            foreground_color = data.get('foreground_color', 'black')
            background_color = data.get('background_color', 'white')
            theme = data.get('theme')
            
            # Generate KD-Code
            image_b64 = generate_kd_code(
                text=text,
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
            
            return jsonify({
                'success': True,
                'kd_code': {
                    'id': f"v2_{datetime.now().timestamp()}",
                    'content': text,
                    'image_data': image_b64,
                    'created_at': datetime.now().isoformat(),
                    'segments_per_ring': segments_per_ring,
                    'anchor_radius': anchor_radius,
                    'ring_width': ring_width,
                    'scale_factor': scale_factor
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v2/scan', methods=['POST'])
    def api_v2_scan():
        """REST API v2 endpoint for scanning KD-Codes"""
        try:
            data = request.get_json()
            
            if not data or 'image_data' not in data:
                return jsonify({'error': 'Image data is required'}), 400
            
            # Extract parameters
            image_data = data['image_data']
            segments_per_ring = data.get('segments_per_ring', 16)
            min_anchor_radius = data.get('min_anchor_radius', 5)
            max_anchor_radius = data.get('max_anchor_radius', 100)
            
            # Decode base64 image
            if image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(image_data)
            
            # Decode KD-Code
            decoded_text = decode_kd_code(
                image_bytes,
                segments_per_ring=segments_per_ring,
                min_anchor_radius=min_anchor_radius,
                max_anchor_radius=max_anchor_radius
            )
            
            if decoded_text is None:
                return jsonify({
                    'success': False,
                    'error': 'No KD-Code detected in image'
                }), 400
            
            return jsonify({
                'success': True,
                'decoded_text': decoded_text
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v2/analytics', methods=['GET'])
    def api_v2_analytics():
        """REST API v2 endpoint for analytics"""
        # In a real implementation, this would fetch from a database
        # For now, we'll return mock analytics
        return jsonify({
            'total_codes': 150,
            'total_scans': 1200,
            'active_users': 45,
            'avg_scan_time': 0.8,
            'top_used_segments': [16, 8, 32],
            'most_popular_themes': ['default', 'business', 'dark']
        })
    
    return app


# Example usage
if __name__ == "__main__":
    # Create and run the GraphQL app
    graphql_app = create_graphql_app()
    print("GraphQL API v2 is ready at /graphql")
    print("REST API v2 endpoints:")
    print("  POST /api/v2/generate - Generate KD-Code")
    print("  POST /api/v2/scan - Scan KD-Code")
    print("  GET /api/v2/analytics - Get analytics")
    
    # For testing purposes, we won't actually run the server here
    # In a real implementation, you would call:
    # graphql_app.run(debug=True, host='0.0.0.0', port=5001)