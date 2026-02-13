"""
Shopify App for KD-Code Integration
Enables KD-Code generation and scanning in Shopify e-commerce stores
"""

import shopify
import json
import base64
from flask import Flask, request, jsonify, session, redirect, url_for
from typing import Dict, Any, Optional
import logging
import os
from urllib.parse import urlparse


class ShopifyKDCodeApp:
    """
    Shopify app integration for KD-Code functionality
    """
    
    def __init__(self, api_key: str, password: str, shared_secret: str, shop_url: str):
        """
        Initialize the Shopify app integration
        
        Args:
            api_key: Shopify app API key
            password: Shopify app password
            shared_secret: Shopify app shared secret
            shop_url: Shopify store URL
        """
        self.api_key = api_key
        self.password = password
        self.shared_secret = shared_secret
        self.shop_url = shop_url
        self.logger = logging.getLogger(__name__)
        
        # Configure Shopify session
        shopify.ShopifyResource.set_site(f"https://{self.api_key}:{self.password}@{shop_url}")
    
    def add_kd_code_to_product(self, product_id: str, content: str) -> bool:
        """
        Add a KD-Code to a Shopify product
        
        Args:
            product_id: Shopify product ID
            content: Content to encode in the KD-Code
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(content)
            
            if not kd_code_b64:
                self.logger.error(f"Failed to generate KD-Code for product {product_id}")
                return False
            
            # Create metafield to store KD-Code
            product = shopify.Product.find(product_id)
            
            # Create/update metafield with KD-Code
            metafields = product.metafields()
            kd_code_exists = False
            
            for metafield in metafields:
                if metafield.namespace == 'kd_code' and metafield.key == 'code_image':
                    # Update existing metafield
                    metafield.value = kd_code_b64
                    metafield.save()
                    kd_code_exists = True
                    break
            
            if not kd_code_exists:
                # Create new metafield
                new_metafield = shopify.Metafield({
                    'namespace': 'kd_code',
                    'key': 'code_image',
                    'value': kd_code_b64,
                    'value_type': 'string'
                })
                
                product.add_metafield(new_metafield)
            
            self.logger.info(f"KD-Code added to product {product_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding KD-Code to product {product_id}: {e}")
            return False
    
    def add_kd_code_to_variant(self, variant_id: str, content: str) -> bool:
        """
        Add a KD-Code to a Shopify product variant
        
        Args:
            variant_id: Shopify product variant ID
            content: Content to encode in the KD-Code
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(content)
            
            if not kd_code_b64:
                self.logger.error(f"Failed to generate KD-Code for variant {variant_id}")
                return False
            
            # Create metafield to store KD-Code
            variant = shopify.Variant.find(variant_id)
            
            # Create/update metafield with KD-Code
            metafields = variant.metafields()
            kd_code_exists = False
            
            for metafield in metafields:
                if metafield.namespace == 'kd_code' and metafield.key == 'code_image':
                    # Update existing metafield
                    metafield.value = kd_code_b64
                    metafield.save()
                    kd_code_exists = True
                    break
            
            if not kd_code_exists:
                # Create new metafield
                new_metafield = shopify.Metafield({
                    'namespace': 'kd_code',
                    'key': 'code_image',
                    'value': kd_code_b64,
                    'value_type': 'string'
                })
                
                variant.add_metafield(new_metafield)
            
            self.logger.info(f"KD-Code added to variant {variant_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding KD-Code to variant {variant_id}: {e}")
            return False
    
    def get_product_kd_code(self, product_id: str) -> Optional[str]:
        """
        Get the KD-Code for a product
        
        Args:
            product_id: Shopify product ID
        
        Returns:
            Base64 encoded KD-Code image or None if not found
        """
        try:
            product = shopify.Product.find(product_id)
            metafields = product.metafields()
            
            for metafield in metafields:
                if metafield.namespace == 'kd_code' and metafield.key == 'code_image':
                    return metafield.value
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting KD-Code for product {product_id}: {e}")
            return None
    
    def create_kd_code_collection(self, title: str, description: str = None) -> Optional[str]:
        """
        Create a Shopify collection for products with KD-Codes
        
        Args:
            title: Collection title
            description: Collection description
        
        Returns:
            Collection ID or None if failed
        """
        try:
            collection = shopify.CustomCollection({
                'title': title,
                'body_html': description or f'<p>Products with KD-Codes: {title}</p>',
                'rules': [
                    {
                        'column': 'tag',
                        'relation': 'equals',
                        'condition': 'has-kdcode'
                    }
                ]
            })
            
            if collection.save():
                self.logger.info(f"KD-Code collection created: {collection.id}")
                return str(collection.id)
            else:
                self.logger.error(f"Failed to create KD-Code collection: {collection.errors}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating KD-Code collection: {e}")
            return None
    
    def add_kd_code_to_order(self, order_id: str, content: str) -> bool:
        """
        Add a KD-Code to a Shopify order
        
        Args:
            order_id: Shopify order ID
            content: Content to encode in the KD-Code
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(content)
            
            if not kd_code_b64:
                self.logger.error(f"Failed to generate KD-Code for order {order_id}")
                return False
            
            # Add to order as note attribute
            order = shopify.Order.find(order_id)
            
            # Update order note attributes
            if not hasattr(order, 'note_attributes'):
                order.note_attributes = []
            
            # Check if KD-Code attribute already exists
            kd_code_attr_exists = False
            for attr in order.note_attributes:
                if attr.get('name') == 'kd_code':
                    attr['value'] = kd_code_b64
                    kd_code_attr_exists = True
                    break
            
            if not kd_code_attr_exists:
                order.note_attributes.append({
                    'name': 'kd_code',
                    'value': kd_code_b64
                })
            
            if order.save():
                self.logger.info(f"KD-Code added to order {order_id}")
                return True
            else:
                self.logger.error(f"Failed to add KD-Code to order {order_id}: {order.errors}")
                return False
        except Exception as e:
            self.logger.error(f"Error adding KD-Code to order {order_id}: {e}")
            return False
    
    def generate_product_kd_codes(self, product_ids: list, content_template: str = None) -> Dict[str, bool]:
        """
        Generate KD-Codes for multiple products
        
        Args:
            product_ids: List of product IDs
            content_template: Template for content generation (optional)
        
        Returns:
            Dictionary mapping product IDs to success status
        """
        results = {}
        
        for product_id in product_ids:
            try:
                # Generate content for this product if template provided
                if content_template:
                    product = shopify.Product.find(product_id)
                    content = content_template.format(
                        product_title=product.title,
                        product_id=product_id,
                        product_handle=product.handle
                    )
                else:
                    # Use product title as content
                    product = shopify.Product.find(product_id)
                    content = f"Product: {product.title} | ID: {product_id}"
                
                success = self.add_kd_code_to_product(product_id, content)
                results[product_id] = success
            except Exception as e:
                self.logger.error(f"Error generating KD-Code for product {product_id}: {e}")
                results[product_id] = False
        
        return results
    
    def scan_kd_code_in_shopify_context(self, image_data: str) -> Optional[Dict[str, Any]]:
        """
        Scan a KD-Code in the Shopify context to retrieve associated data
        
        Args:
            image_data: Base64 encoded image data of the KD-Code
        
        Returns:
            Dictionary with scan results or None if failed
        """
        try:
            from kd_core.decoder import decode_kd_code
            import base64
            
            # Decode the image data
            if image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(image_data)
            
            # Decode the KD-Code
            decoded_text = decode_kd_code(image_bytes)
            
            if not decoded_text:
                return None
            
            # If the decoded text contains product information, try to look it up
            result = {
                'decoded_text': decoded_text,
                'is_product_related': False,
                'product_info': None
            }
            
            # Check if decoded text contains product ID
            if 'Product:' in decoded_text and '| ID:' in decoded_text:
                result['is_product_related'] = True
                # Extract product ID from the decoded text
                try:
                    product_id = decoded_text.split('| ID: ')[1].split()[0]
                    product = shopify.Product.find(product_id)
                    result['product_info'] = {
                        'id': product.id,
                        'title': product.title,
                        'handle': product.handle,
                        'product_type': product.product_type,
                        'vendor': product.vendor
                    }
                except Exception:
                    # Product not found or error retrieving
                    pass
            
            return result
        except Exception as e:
            self.logger.error(f"Error scanning KD-Code in Shopify context: {e}")
            return None


# Flask app for Shopify integration
def create_shopify_app(api_key: str, password: str, shared_secret: str, shop_url: str):
    """
    Create a Flask app for Shopify KD-Code integration
    
    Args:
        api_key: Shopify app API key
        password: Shopify app password
        shared_secret: Shopify app shared secret
        shop_url: Shopify store URL
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Initialize Shopify integration
    shopify_integration = ShopifyKDCodeApp(api_key, password, shared_secret, shop_url)
    
    @app.route('/webhooks/shopify/product-create', methods=['POST'])
    def handle_product_create():
        """Handle Shopify product creation webhook"""
        try:
            # Verify webhook signature
            # In a real implementation, you would verify the X-Shopify-Hmac-SHA256 header
            
            data = request.get_json()
            product_id = data.get('id')
            title = data.get('title')
            
            # Generate KD-Code for new product if enabled
            if os.environ.get('AUTO_GENERATE_KDCODE_FOR_NEW_PRODUCTS', 'false').lower() == 'true':
                content = f"Product: {title} | ID: {product_id}"
                success = shopify_integration.add_kd_code_to_product(str(product_id), content)
                
                if success:
                    return jsonify({'status': 'success', 'kd_code_added': True}), 200
                else:
                    return jsonify({'status': 'partial', 'kd_code_added': False}), 200
            
            return jsonify({'status': 'success', 'kd_code_added': False}), 200
        except Exception as e:
            app.logger.error(f"Error handling product create webhook: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/webhooks/shopify/order-create', methods=['POST'])
    def handle_order_create():
        """Handle Shopify order creation webhook"""
        try:
            data = request.get_json()
            order_id = data.get('id')
            
            # Generate KD-Code for order confirmation if enabled
            if os.environ.get('AUTO_GENERATE_KDCODE_FOR_ORDERS', 'false').lower() == 'true':
                content = f"Order: {order_id} | Status: confirmed"
                success = shopify_integration.add_kd_code_to_order(str(order_id), content)
                
                if success:
                    return jsonify({'status': 'success', 'kd_code_added': True}), 200
                else:
                    return jsonify({'status': 'partial', 'kd_code_added': False}), 200
            
            return jsonify({'status': 'success', 'kd_code_added': False}), 200
        except Exception as e:
            app.logger.error(f"Error handling order create webhook: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/shopify/generate-for-products', methods=['POST'])
    def api_generate_for_products():
        """API endpoint to generate KD-Codes for multiple products"""
        try:
            data = request.get_json()
            product_ids = data.get('product_ids', [])
            content_template = data.get('content_template')
            
            if not product_ids:
                return jsonify({'error': 'Product IDs are required'}), 400
            
            results = shopify_integration.generate_product_kd_codes(product_ids, content_template)
            
            return jsonify({
                'status': 'success',
                'results': results,
                'success_count': sum(1 for success in results.values() if success),
                'total_count': len(results)
            })
        except Exception as e:
            app.logger.error(f"Error in generate_for_products API: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/shopify/scan', methods=['POST'])
    def api_scan_kd_code():
        """API endpoint to scan KD-Codes in Shopify context"""
        try:
            data = request.get_json()
            image_data = data.get('image_data')
            
            if not image_data:
                return jsonify({'error': 'Image data is required'}), 400
            
            result = shopify_integration.scan_kd_code_in_shopify_context(image_data)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'result': result
                })
            else:
                return jsonify({'error': 'No KD-Code detected or error in scanning'}), 400
        except Exception as e:
            app.logger.error(f"Error in scan API: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/shopify/product/<product_id>/kdcode', methods=['GET'])
    def api_get_product_kd_code(product_id):
        """API endpoint to get KD-Code for a specific product"""
        try:
            kd_code = shopify_integration.get_product_kd_code(product_id)
            
            if kd_code:
                return jsonify({
                    'status': 'success',
                    'kd_code': kd_code
                })
            else:
                return jsonify({'error': 'No KD-Code found for this product'}), 404
        except Exception as e:
            app.logger.error(f"Error in get_product_kd_code API: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return app


# Example usage
if __name__ == "__main__":
    # Example of initializing the Shopify integration
    # This would typically be configured with real credentials
    print("Shopify KD-Code Integration Module")
    print("This module provides functions to integrate KD-Codes with Shopify e-commerce stores")
    
    # Example of how to use the integration:
    # shopify_app = create_shopify_app(
    #     api_key=os.environ.get('SHOPIFY_API_KEY'),
    #     password=os.environ.get('SHOPIFY_PASSWORD'),
    #     shared_secret=os.environ.get('SHOPIFY_SHARED_SECRET'),
    #     shop_url=os.environ.get('SHOPIFY_SHOP_URL')
    # )
    #
    # if shopify_app:
    #     print("Shopify app initialized successfully")
    #     shopify_app.run(debug=True, host='0.0.0.0', port=5001)
    # else:
    #     print("Failed to initialize Shopify app")