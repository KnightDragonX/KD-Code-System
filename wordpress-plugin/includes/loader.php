<?php
/**
 * Plugin Loader for KD-Code WordPress Plugin
 * Loads the main plugin file and handles dependencies
 */

// If this file is called directly, abort.
if (!defined('ABSPATH')) {
    die;
}

// Define plugin constants
if (!defined('KDCODE_PLUGIN_VERSION')) {
    define('KDCODE_PLUGIN_VERSION', '1.0.0');
}

if (!defined('KDCODE_PLUGIN_URL')) {
    define('KDCODE_PLUGIN_URL', plugin_dir_url(dirname(__FILE__)));
}

if (!defined('KDCODE_PLUGIN_PATH')) {
    define('KDCODE_PLUGIN_PATH', plugin_dir_path(dirname(__FILE__)));
}

// Check if required PHP version is met
if (version_compare(PHP_VERSION, '7.4', '<')) {
    add_action('admin_notices', function() {
        echo '<div class="notice notice-error"><p>KD-Code plugin requires PHP 7.4 or higher.</p></div>';
    });
    return;
}

// Load the main plugin class
require_once KDCODE_PLUGIN_PATH . 'kdcode-generator.php';

// Activation hook
register_activation_hook(__FILE__, function() {
    // Perform activation tasks
    // Create any required database tables
    // Set default options
    add_option('kdcode_version', KDCODE_PLUGIN_VERSION);
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    // Perform deactivation tasks
    // Clean up any temporary data if needed
});

// Uninstall hook
register_uninstall_hook(__FILE__, function() {
    // Clean up on uninstall
    // Remove plugin options
    delete_option('kdcode_options');
    delete_option('kdcode_version');
});