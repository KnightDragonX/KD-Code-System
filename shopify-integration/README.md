# KD-Code Shopify Integration

A Shopify app that enables generation and integration of KD-Codes in your e-commerce store.

## Overview

The KD-Code Shopify integration allows merchants to generate and use KD-Codes (circular barcodes) for products, orders, and other e-commerce elements. This enhances product authentication, tracking, and customer engagement.

## Features

- **Product Integration**: Add KD-Codes to products for authentication and information
- **Order Integration**: Generate KD-Codes for order confirmation and tracking
- **Variant Support**: Associate KD-Codes with specific product variants
- **Collection Management**: Organize products with KD-Codes into collections
- **Webhook Support**: Real-time synchronization with Shopify events
- **API Endpoints**: Programmatic access to KD-Code functionality
- **Admin UI**: Shopify admin interface for managing KD-Codes

## Installation

### Prerequisites
- Shopify Partner account
- Shopify development store
- KD-Code API service running

### Setup Instructions

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd KD-Code-System/shopify-integration
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Shopify app credentials in environment variables:
   ```bash
   export SHOPIFY_API_KEY="your_api_key"
   export SHOPIFY_API_SECRET="your_api_secret"
   export SHOPIFY_APP_URL="https://your-app-domain.com"
   export KDCODE_API_URL="http://localhost:5000"
   ```

4. Register the app in your Shopify partner dashboard

5. Install the app on your development store

## Configuration

### Shopify App Setup

1. Create a new private app in your Shopify admin
2. Set the required permissions:
   - Products: Read and write
   - Orders: Read and write
   - Customers: Read (optional)
3. Set the app URL to your deployed endpoint
4. Configure webhooks for product and order events

### Environment Variables

Required environment variables:
- `SHOPIFY_API_KEY`: Your Shopify app API key
- `SHOPIFY_API_SECRET`: Your Shopify app API secret
- `SHOPIFY_APP_URL`: URL where your app is hosted
- `KDCODE_API_URL`: URL of your KD-Code API service
- `FLASK_SECRET_KEY`: Secret key for Flask sessions

## Usage

### In the Shopify Admin

1. Navigate to a product page
2. Use the KD-Code generator to create a code for the product
3. The KD-Code will be stored as a metafield on the product
4. The code will be displayed on the product page

### API Endpoints

#### Generate KD-Code for Products
```
POST /api/shopify/generate-for-products
Content-Type: application/json

{
  "product_ids": ["123456789", "987654321"],
  "content_template": "Product: {{product_title}} | ID: {{product_id}}"
}
```

#### Scan KD-Code in Shopify Context
```
POST /api/shopify/scan
Content-Type: application/json

{
  "image_data": "data:image/png;base64,..."
}
```

#### Get Product KD-Code
```
GET /api/shopify/product/{product_id}/kdcode
```

## Webhooks

The app listens for the following Shopify webhooks:

- `products/create`: Automatically generate KD-Codes for new products (if configured)
- `orders/create`: Generate KD-Codes for new orders (if configured)

## Development

### Running Locally

```bash
python kdcode_shopify_app.py
```

### Testing

The integration includes webhook handlers and API endpoints that can be tested with ngrok for local development:

```bash
ngrok http 5000
```

Then update your Shopify app configuration with the ngrok URL.

## Security

- All API calls are authenticated
- Webhook signatures are verified
- Input validation is performed on all endpoints
- Rate limiting is implemented to prevent abuse

## Support

For support, please create an issue in the GitHub repository or contact the development team.

## License

MIT License