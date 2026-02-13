document.addEventListener('DOMContentLoaded', function() {
  // Tab switching functionality
  const tabs = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Remove active class from all tabs and contents
      tabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      // Add active class to clicked tab and corresponding content
      tab.classList.add('active');
      const tabName = tab.getAttribute('data-tab');
      document.getElementById(`${tabName}-tab`).classList.add('active');
    });
  });
  
  // Generate button functionality
  const generateBtn = document.getElementById('generate-btn');
  const textInput = document.getElementById('text-input');
  const kdCodeDisplay = document.getElementById('kd-code-display');
  
  generateBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      alert('Please enter text to encode');
      return;
    }
    
    try {
      generateBtn.disabled = true;
      generateBtn.textContent = 'Generating...';
      
      // Call the KD-Code API
      const response = await fetch('http://localhost:5000/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: text })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        // Display the generated KD-Code
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${data.image}`;
        img.alt = 'Generated KD-Code';
        img.className = 'kd-code-image';
        
        kdCodeDisplay.innerHTML = '';
        kdCodeDisplay.appendChild(img);
      } else {
        alert(`Error: ${data.error || 'Failed to generate KD-Code'}`);
      }
    } catch (error) {
      console.error('Error generating KD-Code:', error);
      alert('Error generating KD-Code. Please try again.');
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = 'Generate KD-Code';
    }
  });
});