# KD-Code WordPress/WooCommerce Plugin

A WordPress plugin that integrates KD-Code functionality directly into your WordPress site and WooCommerce store.

## Overview

The KD-Code WordPress plugin allows you to generate and scan KD-Codes (circular barcodes) directly from your WordPress site. It provides both frontend and backend functionality for creating and using KD-Codes in various contexts.

## Features

- **KD-Code Generation**: Generate KD-Codes from any text directly in WordPress
- **WooCommerce Integration**: Add KD-Codes to products for authentication, tracking, or information
- **Shortcode Support**: Use `[kdcode_generate text="Your text"]` to generate codes anywhere
- **Admin Dashboard**: Manage KD-Code settings and view usage statistics
- **API Integration**: Connect to your KD-Code service API
- **Bulk Operations**: Generate multiple KD-Codes at once
- **Import/Export**: Import/export KD-Codes in various formats
- **Responsive Design**: Works on all device sizes

## Installation

### Prerequisites
- WordPress 5.0 or higher
- PHP 7.4 or higher
- KD-Code API service running (either locally or remotely)

### Manual Installation
1. Download the plugin files
2. Create a `kdcode-generator` folder in your `/wp-content/plugins/` directory
3. Copy all files to this folder
4. Activate the plugin through the 'Plugins' menu in WordPress
5. Configure the API settings in Settings > KD-Code

### Via WordPress Admin
1. Go to Plugins > Add New
2. Click "Upload Plugin"
3. Select the plugin ZIP file
4. Click "Install Now"
5. Activate the plugin
6. Configure the API settings in Settings > KD-Code

## Configuration

1. Navigate to Settings > KD-Code in your WordPress admin
2. Enter your KD-Code API base URL (e.g., `http://localhost:5000`)
3. If required, enter your API key
4. Save the settings

## Usage

### Shortcodes

#### Basic Generation
```
[kdcode_generate text="Hello World"]
```

#### With Custom Parameters
```
[kdcode_generate text="Custom KD-Code" size="large" title="My Code"]
```

#### Display Existing Code
```
[kdcode_display image="path/to/image.png" title="Existing Code"]
```

### WooCommerce Integration

The plugin adds a KD-Code field to your product edit pages. Enter content in the "KD-Code Content" field to generate a unique KD-Code for that product. The code will be displayed on the product page.

### Admin Panel

Access the admin panel through Settings > KD-Code to:
- Configure API settings
- Test API connectivity
- Perform bulk operations
- View usage statistics
- Import/export codes

## API Integration

The plugin connects to your KD-Code service API to generate and scan codes. Make sure your API service is running and accessible from your WordPress server.

### Required Endpoints
- `POST /api/generate` - For generating KD-Codes
- `POST /api/scan` - For scanning KD-Codes (planned feature)

## Hooks and Filters

### Actions
- `kdcode_before_generate` - Runs before KD-Code generation
- `kdcode_after_generate` - Runs after successful generation
- `kdcode_generation_error` - Runs when generation fails

### Filters
- `kdcode_default_size` - Modify default KD-Code size
- `kdcode_generation_params` - Modify parameters sent to API

## Development

### Adding New Features
1. Create new functions in the main plugin file
2. Add corresponding admin UI elements
3. Implement AJAX handlers for frontend interactions
4. Update the JavaScript files as needed

### Custom Styling
The plugin includes CSS files in the `assets/css/` directory. You can modify these or add custom styles through your theme.

## Troubleshooting

### Common Issues
- **API Connection Errors**: Verify your API URL and credentials in settings
- **CORS Issues**: Ensure your KD-Code API allows requests from your WordPress domain
- **Permission Errors**: Check that your web server has write permissions to the plugin directory

### Debug Mode
Enable debug mode in the settings to get more detailed error information.

## Security

- The plugin uses WordPress nonces for security
- All user inputs are sanitized
- API keys are stored securely in WordPress options
- File uploads are validated for security

## Support

For support, please create an issue in the GitHub repository or contact the development team.

## License

This plugin is licensed under the GPL v2 or later license.