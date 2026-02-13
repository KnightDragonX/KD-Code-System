<?php
/**
 * KD-Code WordPress/WooCommerce Plugin
 * 
 * @package           KDCode
 * @author            KD-Code Team
 * @copyright         2023 KD-Code System
 * @license           GPL-2.0-or-later
 *
 * @wordpress-plugin
 * Plugin Name:       KD-Code Generator
 * Plugin URI:        https://kd-code.example.com
 * Description:       Generate and scan KD-Codes directly in WordPress and WooCommerce.
 * Version:           1.0.0
 * Requires at least: 5.0
 * Requires PHP:      7.4
 * Author:            KD-Code System
 * Author URI:        https://kd-code.example.com
 * Text Domain:       kdcode
 * License:           GPL v2 or later
 * License URI:       http://www.gnu.org/licenses/gpl-2.0.txt
 */

// If this file is called directly, abort.
if (!defined('ABSPATH')) {
    die;
}

// Define plugin constants
define('KDCODE_PLUGIN_VERSION', '1.0.0');
define('KDCODE_PLUGIN_URL', plugin_dir_url(__FILE__));
define('KDCODE_PLUGIN_PATH', plugin_dir_path(__FILE__));
define('KDCODE_API_BASE_URL', 'http://localhost:5000'); // Default API URL

class KDCodeWordPressPlugin {
    
    public function __construct() {
        // Initialize hooks
        add_action('init', array($this, 'init'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        add_action('admin_enqueue_scripts', array($this, 'admin_enqueue_scripts'));
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'settings_init'));
        
        // Shortcode for generating KD-Codes
        add_shortcode('kdcode_generate', array($this, 'generate_shortcode'));
        add_shortcode('kdcode_display', array($this, 'display_shortcode'));
        
        // WooCommerce hooks
        add_action('woocommerce_product_options_general_product_data', array($this, 'add_kdcode_field'));
        add_action('woocommerce_process_product_meta', array($this, 'save_kdcode_field'));
        add_action('woocommerce_single_product_summary', array($this, 'display_product_kdcode'), 25);
    }
    
    /**
     * Initialize the plugin
     */
    public function init() {
        // Load translations
        load_plugin_textdomain('kdcode', false, dirname(plugin_basename(__FILE__)) . '/languages');
    }
    
    /**
     * Enqueue frontend scripts and styles
     */
    public function enqueue_scripts() {
        wp_enqueue_script('kdcode-frontend-js', KDCODE_PLUGIN_URL . 'assets/js/frontend.js', array('jquery'), KDCODE_PLUGIN_VERSION, true);
        wp_enqueue_style('kdcode-frontend-css', KDCODE_PLUGIN_URL . 'assets/css/frontend.css', array(), KDCODE_PLUGIN_VERSION);
        
        // Localize script for AJAX calls
        wp_localize_script('kdcode-frontend-js', 'kdcode_ajax', array(
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('kdcode_nonce')
        ));
    }
    
    /**
     * Enqueue admin scripts and styles
     */
    public function admin_enqueue_scripts($hook) {
        if ($hook !== 'settings_page_kdcode-settings') {
            return;
        }
        
        wp_enqueue_script('kdcode-admin-js', KDCODE_PLUGIN_URL . 'assets/js/admin.js', array('jquery'), KDCODE_PLUGIN_VERSION, true);
        wp_enqueue_style('kdcode-admin-css', KDCODE_PLUGIN_URL . 'assets/css/admin.css', array(), KDCODE_PLUGIN_VERSION);
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'KD-Code Settings',
            'KD-Code',
            'manage_options',
            'kdcode-settings',
            array($this, 'settings_page')
        );
    }
    
    /**
     * Initialize settings
     */
    public function settings_init() {
        register_setting('kdcode_settings', 'kdcode_options');
        
        add_settings_section(
            'kdcode_settings_section',
            'KD-Code API Settings',
            array($this, 'settings_section_callback'),
            'kdcode-settings'
        );
        
        add_settings_field(
            'kdcode_api_url',
            'API Base URL',
            array($this, 'api_url_render'),
            'kdcode-settings',
            'kdcode_settings_section'
        );
        
        add_settings_field(
            'kdcode_api_key',
            'API Key',
            array($this, 'api_key_render'),
            'kdcode-settings',
            'kdcode_settings_section'
        );
    }
    
    /**
     * Render API URL field
     */
    public function api_url_render() {
        $options = get_option('kdcode_options');
        ?>
        <input type='text' name='kdcode_options[api_url]' value='<?php echo $options['api_url'] ?? KDCODE_API_BASE_URL; ?>' style="width: 100%; max-width: 500px;">
        <p class="description">Enter the base URL for your KD-Code API service (e.g., http://localhost:5000)</p>
        <?php
    }
    
    /**
     * Render API Key field
     */
    public function api_key_render() {
        $options = get_option('kdcode_options');
        ?>
        <input type='password' name='kdcode_options[api_key]' value='<?php echo $options['api_key'] ?? ''; ?>' style="width: 100%; max-width: 500px;">
        <p class="description">Enter your API key for authentication (if required)</p>
        <?php
    }
    
    /**
     * Settings section callback
     */
    public function settings_section_callback() {
        echo __('Configure your KD-Code API settings:', 'kdcode');
    }
    
    /**
     * Settings page
     */
    public function settings_page() {
        ?>
        <div class="wrap">
            <h1>KD-Code Settings</h1>
            <form action='options.php' method='post'>
                <?php
                settings_fields('kdcode_settings');
                do_settings_sections('kdcode-settings');
                submit_button();
                ?>
            </form>
        </div>
        <?php
    }
    
    /**
     * Generate shortcode handler
     */
    public function generate_shortcode($atts) {
        $atts = shortcode_atts(array(
            'text' => '',
            'size' => 'medium',
            'title' => 'KD-Code'
        ), $atts);
        
        if (empty($atts['text'])) {
            return '<p>Error: Text attribute is required for KD-Code generation</p>';
        }
        
        // Generate KD-Code via API
        $kd_code_image = $this->generate_kd_code_via_api($atts['text']);
        
        if (!$kd_code_image) {
            return '<p>Error: Failed to generate KD-Code</p>';
        }
        
        $size_class = 'kdcode-' . $atts['size'];
        
        ob_start();
        ?>
        <div class="kdcode-container <?php echo esc_attr($size_class); ?>">
            <h3><?php echo esc_html($atts['title']); ?></h3>
            <img src="data:image/png;base64,<?php echo esc_attr($kd_code_image); ?>" alt="<?php echo esc_attr($atts['title']); ?>" class="kdcode-image">
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Display shortcode handler
     */
    public function display_shortcode($atts) {
        $atts = shortcode_atts(array(
            'image' => '',
            'title' => 'KD-Code'
        ), $atts);
        
        if (empty($atts['image'])) {
            return '<p>Error: Image attribute is required for KD-Code display</p>';
        }
        
        ob_start();
        ?>
        <div class="kdcode-display-container">
            <h3><?php echo esc_html($atts['title']); ?></h3>
            <img src="<?php echo esc_url($atts['image']); ?>" alt="<?php echo esc_attr($atts['title']); ?>" class="kdcode-display-image">
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Generate KD-Code via API
     */
    private function generate_kd_code_via_api($text) {
        $options = get_option('kdcode_options');
        $api_url = $options['api_url'] ?? KDCODE_API_BASE_URL;
        
        $api_endpoint = $api_url . '/api/generate';
        
        $response = wp_remote_post($api_endpoint, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'Authorization' => !empty($options['api_key']) ? 'Bearer ' . $options['api_key'] : ''
            ),
            'body' => json_encode(array('text' => $text)),
            'timeout' => 30
        ));
        
        if (is_wp_error($response)) {
            error_log('KD-Code API error: ' . $response->get_error_message());
            return false;
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if (isset($data['image'])) {
            return $data['image'];
        }
        
        error_log('KD-Code API response error: ' . $body);
        return false;
    }
    
    /**
     * Add KD-Code field to product data in WooCommerce
     */
    public function add_kdcode_field() {
        woocommerce_wp_textarea(array(
            'id' => '_kdcode_content',
            'label' => __('KD-Code Content', 'kdcode'),
            'placeholder' => __('Enter content for KD-Code generation', 'kdcode'),
            'desc_tip' => 'true',
            'description' => __('Content to encode in the product KD-Code', 'kdcode')
        ));
    }
    
    /**
     * Save KD-Code field in product meta
     */
    public function save_kdcode_field($post_id) {
        $kdcode_content = $_POST['_kdcode_content'] ?? '';
        if (!empty($kdcode_content)) {
            update_post_meta($post_id, '_kdcode_content', sanitize_textarea_field($kdcode_content));
            
            // Generate and save KD-Code image
            $kdcode_image = $this->generate_kd_code_via_api($kdcode_content);
            if ($kdcode_image) {
                update_post_meta($post_id, '_kdcode_image', $kdcode_image);
            }
        }
    }
    
    /**
     * Display product KD-Code on single product page
     */
    public function display_product_kdcode() {
        global $product;
        
        $kdcode_content = get_post_meta($product->get_id(), '_kdcode_content', true);
        $kdcode_image = get_post_meta($product->get_id(), '_kdcode_image', true);
        
        if (!empty($kdcode_content) && !empty($kdcode_image)) {
            echo '<div class="product-kdcode-section">';
            echo '<h4>Product KD-Code</h4>';
            echo '<div class="product-kdcode-container">';
            echo '<img src="data:image/png;base64,' . esc_attr($kdcode_image) . '" alt="Product KD-Code" class="product-kdcode-image">';
            echo '</div>';
            echo '</div>';
        }
    }
}

// Initialize the plugin
function run_kdcode_wordpress_plugin() {
    $plugin = new KDCodeWordPressPlugin();
    return $plugin;
}

// Start the plugin
$kdcode_wordpress_plugin = run_kdcode_wordpress_plugin();

// AJAX handlers
add_action('wp_ajax_generate_kdcode', 'handle_generate_kdcode_ajax');
add_action('wp_ajax_nopriv_generate_kdcode', 'handle_generate_kdcode_ajax');

function handle_generate_kdcode_ajax() {
    // Verify nonce
    if (!wp_verify_nonce($_POST['nonce'], 'kdcode_nonce')) {
        wp_die('Security check failed');
    }
    
    $text = sanitize_text_field($_POST['text']);
    
    if (empty($text)) {
        wp_send_json_error('Text is required');
    }
    
    // Generate KD-Code
    $options = get_option('kdcode_options');
    $api_url = $options['api_url'] ?? KDCODE_API_BASE_URL;
    
    $api_endpoint = $api_url . '/api/generate';
    
    $response = wp_remote_post($api_endpoint, array(
        'headers' => array(
            'Content-Type' => 'application/json',
            'Authorization' => !empty($options['api_key']) ? 'Bearer ' . $options['api_key'] : ''
        ),
        'body' => json_encode(array('text' => $text)),
        'timeout' => 30
    ));
    
    if (is_wp_error($response)) {
        wp_send_json_error($response->get_error_message());
    }
    
    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);
    
    if (isset($data['image'])) {
        wp_send_json_success(array(
            'image' => $data['image'],
            'status' => $data['status'] ?? 'success'
        ));
    } else {
        wp_send_json_error($data['error'] ?? 'Unknown error');
    }
}
?>