/**
 * KD-Code WordPress Plugin Admin JavaScript
 * Handles admin panel functionality
 */

jQuery(document).ready(function($) {
    // Handle test API connection
    $('#test-api-connection').on('click', function(e) {
        e.preventDefault();
        
        const apiUrl = $('#kdcode_options\\[api_url\\]').val();
        const apiKey = $('#kdcode_options\\[api_key\\]').val();
        
        if (!apiUrl) {
            alert('Please enter an API URL first');
            return;
        }
        
        // Disable button and show loading
        $(this).prop('disabled', true).text('Testing...');
        
        // Test the API connection
        $.ajax({
            url: ajaxurl,
            type: 'POST',
            data: {
                action: 'test_kdcode_api_connection',
                api_url: apiUrl,
                api_key: apiKey,
                nonce: kdcode_ajax.nonce
            },
            success: function(response) {
                if (response.success) {
                    alert('API connection successful!');
                } else {
                    alert('API connection failed: ' + response.data);
                }
            },
            error: function(xhr, status, error) {
                alert('Error testing API connection: ' + error);
            },
            complete: function() {
                // Reset button
                $('#test-api-connection').prop('disabled', false).text('Test Connection');
            }
        });
    });
    
    // Handle bulk generation in admin
    $('#bulk-generate-kdcodes').on('click', function(e) {
        e.preventDefault();
        
        const textInputs = $('.bulk-kdcode-text');
        const resultsContainer = $('#bulk-generation-results');
        
        resultsContainer.empty().append('<p>Generating KD-Codes in bulk...</p>');
        
        // Collect all texts to generate
        const texts = [];
        textInputs.each(function() {
            const text = $(this).val().trim();
            if (text) {
                texts.push(text);
            }
        });
        
        if (texts.length === 0) {
            resultsContainer.html('<p class="error">No valid texts found for generation</p>');
            return;
        }
        
        // Disable button during processing
        $(this).prop('disabled', true).text('Generating...');
        
        // Generate in bulk
        $.ajax({
            url: ajaxurl,
            type: 'POST',
            data: {
                action: 'bulk_generate_kdcodes',
                texts: texts,
                nonce: kdcode_ajax.nonce
            },
            success: function(response) {
                if (response.success) {
                    resultsContainer.html('<p>Successfully generated ' + response.data.count + ' KD-Codes</p>');
                    
                    // Display generated codes
                    const codesContainer = $('<div class="bulk-codes-container"></div>');
                    $.each(response.data.codes, function(index, codeData) {
                        const codeDiv = $('<div class="bulk-code-item"><h4>' + codeData.text.substring(0, 30) + '...</h4><img src="data:image/png;base64,' + codeData.image + '" alt="KD-Code" class="kdcode-image"></div>');
                        codesContainer.append(codeDiv);
                    });
                    
                    resultsContainer.append(codesContainer);
                } else {
                    resultsContainer.html('<p class="error">Bulk generation failed: ' + response.data + '</p>');
                }
            },
            error: function(xhr, status, error) {
                resultsContainer.html('<p class="error">Error in bulk generation: ' + error + '</p>');
            },
            complete: function() {
                // Reset button
                $('#bulk-generate-kdcodes').prop('disabled', false).text('Bulk Generate KD-Codes');
            }
        });
    });
    
    // Handle import/export functionality
    $('#import-kdcodes').on('click', function(e) {
        e.preventDefault();
        
        const fileInput = $('#import-file')[0];
        if (!fileInput.files[0]) {
            alert('Please select a file to import');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('action', 'import_kdcodes');
        formData.append('nonce', kdcode_ajax.nonce);
        
        $.ajax({
            url: ajaxurl,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.success) {
                    alert('Successfully imported ' + response.data.count + ' KD-Codes');
                } else {
                    alert('Import failed: ' + response.data);
                }
            },
            error: function(xhr, status, error) {
                alert('Import error: ' + error);
            }
        });
    });
    
    $('#export-kdcodes').on('click', function(e) {
        e.preventDefault();
        
        // Trigger export
        $.ajax({
            url: ajaxurl,
            type: 'POST',
            data: {
                action: 'export_kdcodes',
                nonce: kdcode_ajax.nonce
            },
            success: function(response) {
                if (response.success) {
                    // Create download link
                    const link = document.createElement('a');
                    link.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(response.data.codes, null, 2));
                    link.download = 'kd-codes-export.json';
                    link.click();
                } else {
                    alert('Export failed: ' + response.data);
                }
            },
            error: function(xhr, status, error) {
                alert('Export error: ' + error);
            }
        });
    });
});

// Admin utility functions
function updateStats() {
    jQuery.ajax({
        url: ajaxurl,
        type: 'POST',
        data: {
            action: 'get_kdcode_stats',
            nonce: kdcode_ajax.nonce
        },
        success: function(response) {
            if (response.success) {
                // Update stats display
                jQuery('#kdcode-stats-count').text(response.data.total_codes);
                jQuery('#kdcode-stats-scans').text(response.data.total_scans);
                jQuery('#kdcode-stats-users').text(response.data.active_users);
            }
        }
    });
}

// Auto-update stats every 30 seconds
if (jQuery('#kdcode-stats-container').length) {
    setInterval(updateStats, 30000);
    updateStats(); // Initial update
}