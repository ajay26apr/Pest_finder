window.onload = function() {
    const video = document.getElementById('camera');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('capture-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const resultsDiv = document.getElementById('results');

    // Access the user's camera
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            video.srcObject = stream;
        })
        .catch((err) => {
            console.error("Error accessing camera: ", err);
        });

    // Capture the image from the video
    captureBtn.onclick = function() {
        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw the current frame from the video to the canvas
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        // Show the "Process Image" button
        uploadBtn.style.display = 'inline';
    };

    // Process the captured image and send it to Flask
    uploadBtn.onclick = function() {
        const imageDataUrl = canvas.toDataURL('image/jpeg');  // Capture image as base64

        // Send the base64 image data to the Flask server
        fetch('/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: imageDataUrl })
        })
        .then(response => response.json())
        .then(data => {
            // Display the extracted text and Gemini response
            if (data.extracted_text) {
                resultsDiv.innerHTML = `<h3>Extracted Text:</h3><p>${data.extracted_text}</p>`;
            }
            if (data.gemini_response) {
                resultsDiv.innerHTML += `<h3>Gemini Response:</h3><p>${data.gemini_response}</p>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    };
};
