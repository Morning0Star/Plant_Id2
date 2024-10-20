import cv2
import torch
import requests
from io import BytesIO
from PIL import Image
import numpy as np

# YOLOv5 model and PlantNET API configuration
MODEL_PATH = 'C:/Users/kusha/OneDrive/Desktop/yolov11_project/yolov5/runs/train/exp/weights/best.pt'
API_KEY = '2b10sFh3wPJUbaYhfnHONlQO'
API_URL = 'https://my-api.plantnet.org/v2/identify/all'

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)

# Function to process an image
def process_image(image_data, uploaded_image_name):
    # Convert byte data to a NumPy array
    np_img = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    
    # Run YOLOv5 detection
    results = model(image)
    detections = results.xyxy[0]
    results_list = []

    for det in detections:
        x1, y1, x2, y2, conf, cls = map(int, det[:6])
        cropped_image = image[y1:y2, x1:x2]

        # Convert cropped image to PIL format
        cropped_pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))

        # Convert PIL image to bytes for in-memory processing
        img_buffer = BytesIO()
        cropped_pil_image.save(img_buffer, format='JPEG')
        img_buffer.seek(0)

        # Use PlantNET API for plant identification
        img_bytes = img_buffer.getvalue()
        files = {'images': ('cropped_image.jpg', img_bytes, 'image/jpeg')}
        params = {
            'api-key': API_KEY,
            'lang': 'en',
            'include-related-images': False,
            'nb-results': 5,
            'no-reject': False
        }
        response = requests.post(API_URL, params=params, files=files)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('results'):
                best_match = max(response_data['results'], key=lambda x: x['score'])
                identified_plant = best_match['species']['scientificNameWithoutAuthor']
                confidence_rate = best_match['score']

                # Store results in a list
                results_list.append({
                    'Cropped Image': img_buffer.getvalue(),  # Return the raw byte data
                    'Identified Plant': identified_plant,
                    'Confidence': confidence_rate
                })

    return results_list
