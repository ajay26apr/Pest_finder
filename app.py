import os
from flask import Flask, render_template, request, jsonify
import easyocr
import base64
from typing import List, Type
from pydantic import BaseModel, create_model
import google.generativeai as genai  # Ensure the Gemini Flash API SDK is installed

app = Flask(__name__)

# Configure folder to save temporary images
UPLOAD_FOLDER = 'uploaded_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def process_image(image_path, lang_list=['en', 'te'], confidence_threshold=0.7):
    """
    Process an image to extract high-confidence text using EasyOCR.
    Args:
        image_path (str): Path to the image file.
        lang_list (list): List of languages for OCR (e.g., English, Telugu).
        confidence_threshold (float): Minimum confidence score for text to be included.
    Returns:
        str: Filtered and concatenated text.
    """
    reader = easyocr.Reader(lang_list)
    results = reader.readtext(image_path)

    # Filter results based on confidence
    extracted_texts = [
        text for _, text, confidence in results if confidence >= confidence_threshold
    ]

    # Combine extracted text into a single prompt
    return " ".join(extracted_texts)


def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    """
    Dynamically create a Pydantic model with specified field names.
    Args:
        field_names (List[str]): List of field names for the model.
    Returns:
        Type[BaseModel]: Generated Pydantic model.
    """
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model("DynamicListingModel", **field_definitions)


def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Create a container model for listings using a Pydantic model.
    Args:
        listing_model (Type[BaseModel]): Listing model to wrap in a container.
    Returns:
        Type[BaseModel]: Container Pydantic model.
    """
    return create_model("DynamicListingsContainer", listings=(List[listing_model], ...))


def gemini_generate_response(prompt, container_model):
    """
    Generate a response using the Gemini Flash API.
    Args:
        prompt (str): The prompt to send to the API.
        container_model (Type[BaseModel]): Pydantic model for response validation.
    Returns:
        str: Processed response from the API.
    """
    try:
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": container_model
            }
        )
        response = model.generate_content(prompt)
        print(response)  # Debug: Print raw API response
        if response and response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handle the homepage route. Accepts a POST request for image processing
    and sends the extracted text to Gemini Flash API.
    """
    if request.method == 'POST':
        # Get the base64 encoded image from the client
        data_url = request.json.get('image')
        if not data_url:
            return jsonify({'error': 'No image data provided'}), 400

        # Decode the base64 image data
        image_data = base64.b64decode(data_url.split(',')[1])
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_image.jpg')
        with open(image_path, 'wb') as image_file:
            image_file.write(image_data)

        # Process the image and extract high-confidence text
        extracted_text = process_image(image_path)

        if not extracted_text:
            return jsonify({'error': 'No text extracted from the image'}), 400

        # Define fields for the Pydantic model
        fields = ['Product Name', 'Description', 'Usage Instructions']

        # Create Pydantic models dynamically
        listing_model = create_dynamic_listing_model(fields)
        container_model = create_listings_container_model(listing_model)

        # Create a prompt with extracted text
        system_message = (
            "Act as an agriculture expert. Provide all details about the product "
            "including its uses, chemical composition, and benefits. "
            "Here is the product information: "
        )
        prompt = f"{system_message}{extracted_text}"

        # Generate response from Gemini Flash API
        response = gemini_generate_response(prompt, container_model)

        # Cleanup the uploaded image
        os.remove(image_path)

        return jsonify({'extracted_text': extracted_text, 'gemini_response': response})

    # Render the HTML template for GET requests
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
