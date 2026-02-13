/**
 * KD-Code WordPress Plugin JavaScript
 * Handles frontend interactions for KD-Code generation and display
 */

jQuery(document).ready(function($) {
    // Handle dynamic KD-Code generation
    $('.kdcode-dynamic-generate').on('click', function(e) {
        e.preventDefault();
        
        const textInput = $(this).siblings('.kdcode-text-input').val();
        const container = $(this).closest('.kdcode-container').find('.kdcode-result');
        
        if (!textInput) {
            alert('Please enter text to generate KD-Code');
            return;
        }
        
        // Show loading indicator
        container.html('<div class="kdcode-loading">Generating...</div>');
        
        // Make AJAX request to generate KD-Code
        $.ajax({
            url: kdcode_ajax.ajax_url,
            type: 'POST',
            data: {
                action: 'generate_kdcode',
                text: textInput,
                nonce: kdcode_ajax.nonce
            },
            success: function(response) {
                if (response.success) {
                    container.html('<img src="data:image/png;base64,' + response.data.image + '" alt="Generated KD-Code" class="kdcode-image">');
                } else {
                    container.html('<div class="kdcode-error">Error: ' + response.data + '</div>');
                }
            },
            error: function(xhr, status, error) {
                container.html('<div class="kdcode-error">Error: ' + error + '</div>');
            }
        });
    });
    
    // Handle WooCommerce product KD-Code generation
    $('#generate-product-kdcode').on('click', function(e) {
        e.preventDefault();
        
        const productId = $(this).data('product-id');
        const textContent = $('#kdcode-content-' + productId).val();
        
        if (!textContent) {
            alert('Please enter content for KD-Code generation');
            return;
        }
        
        // Show loading
        $(this).prop('disabled', true).text('Generating...');
        
        $.ajax({
            url: kdcode_ajax.ajax_url,
            type: 'POST',
            data: {
                action: 'generate_kdcode',
                text: textContent,
                nonce: kdcode_ajax.nonce
            },
            success: function(response) {
                if (response.success) {
                    // Update product KD-Code display
                    $('#product-kdcode-display-' + productId).html(
                        '<img src="data:image/png;base64,' + response.data.image + '" alt="Product KD-Code" class="product-kdcode-image">'
                    );
                } else {
                    alert('Error generating KD-Code: ' + response.data);
                }
            },
            error: function(xhr, status, error) {
                alert('Error generating KD-Code: ' + error);
            },
            complete: function() {
                // Reset button
                $('#generate-product-kdcode').prop('disabled', false).text('Generate KD-Code');
            }
        });
    });
    
    // Handle scan functionality if camera access is available
    $('.kdcode-scan-trigger').on('click', function(e) {
        e.preventDefault();
        
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            // Access camera
            navigator.mediaDevices.getUserMedia({ video: true }).then(function(stream) {
                // Create video element to display camera feed
                const video = document.createElement('video');
                video.srcObject = stream;
                video.play();
                
                // Add video to page
                const container = $(this).closest('.kdcode-container');
                container.append(video);
                
                // TODO: Implement actual scanning logic using KD-Code scanning library
                // This would involve capturing frames and sending to backend for processing
            }).catch(function(err) {
                console.error("Error accessing camera: ", err);
                alert("Could not access camera: " + err.message);
            });
        } else {
            alert("Camera access not supported in this browser");
        }
    });
    
    // Handle file upload for scanning
    $('.kdcode-upload-trigger').on('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(event) {
            const imageData = event.target.result;
            
            // Send to backend for scanning
            $.ajax({
                url: kdcode_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'scan_kdcode',
                    image_data: imageData,
                    nonce: kdcode_ajax.nonce
                },
                success: function(response) {
                    if (response.success) {
                        $('#kdcode-scan-result').text('Scanned content: ' + response.data.decoded_text);
                    } else {
                        $('#kdcode-scan-result').text('Error: ' + response.data);
                    }
                },
                error: function(xhr, status, error) {
                    $('#kdcode-scan-result').text('Error: ' + error);
                }
            });
        };
        reader.readAsDataURL(file);
    });
});

// Utility functions
function validateKDCodeText(text) {
    // Validate text for KD-Code generation
    if (!text || typeof text !== 'string') {
        return false;
    }
    
    // Check length
    if (text.length > 128) {
        return false;
    }
    
    return true;
}

function displayKDCodeInContainer(containerId, imageData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const img = document.createElement('img');
    img.src = 'data:image/png;base64,' + imageData;
    img.alt = 'KD-Code';
    img.className = 'kdcode-image';
    
    // Clear container and add image
    container.innerHTML = '';
    container.appendChild(img);
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateKDCodeText: validateKDCodeText,
        displayKDCodeInContainer: displayKDCodeInContainer
    };
}