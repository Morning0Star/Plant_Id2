import streamlit as st
import pandas as pd
import zipfile
import backend  # Import your backend module for image processing
from pymongo import MongoClient
from io import BytesIO

# Set page title
st.title("Plant Identification App")

# MongoDB connection details
MONGO_URL = "mongodb+srv://Regreen:TreeMendUs@cluster0.f4l7h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Initialize MongoDB connection and collection
client = MongoClient(MONGO_URL)
db = client['plant_identification']
collection = db['history']

# Fetch history from MongoDB
def fetch_history():
    return list(collection.find())

# Update existing records in MongoDB
def update_history(uploaded_image, corrected_plant):
    existing_entry = collection.find_one({'uploaded_image': uploaded_image})
    
    if existing_entry:
        collection.update_one(
            {'uploaded_image': uploaded_image},
            {'$set': {'corrected_plant': corrected_plant}}
        )
        st.success(f"Successfully updated {uploaded_image} with corrected plant name: {corrected_plant}.")
    else:
        st.warning(f"No existing entry found for {uploaded_image}.")

# Initialize session state for uploaded images and data
if 'uploaded_images' not in st.session_state:
    st.session_state.uploaded_images = []
if 'current_data' not in st.session_state:
    st.session_state.current_data = {}

# Process folder (zip file) upload
def handle_folder_upload(zip_file):
    # Clear previous uploaded images and data
    st.session_state.uploaded_images.clear()
    st.session_state.current_data.clear()

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith(('.jpg', '.jpeg', '.png')):
                with zip_ref.open(file_name) as img_file:
                    process_image(img_file.read(), file_name)   

# Process individual image files
def process_image(image_data, uploaded_image_name):
    # Check if the image has already been uploaded
    existing_entry = collection.find_one({'uploaded_image': uploaded_image_name})
    if existing_entry:
        st.warning(f"{uploaded_image_name} already exists in the database.")
        corrected_plant = existing_entry.get('corrected_plant', None)
        identified_plant = existing_entry.get('identified_plant', None)
        confidence = existing_entry.get('confidence', None)

        # Display existing entry
        col1, col2 = st.columns(2)
        with col1:
            st.image(image_data, caption="Uploaded Image", use_column_width=True)
        with col2:
            st.write(f"Identified Plant: {identified_plant} (Confidence: {confidence:.2f})")

        # Text input for corrected plant name with a unique key
        corrected_plant_input = st.text_input(f"Corrected Plant for {uploaded_image_name}:", value=corrected_plant, key=f"{uploaded_image_name}_correction")

        # Button to save correction
        if st.button(f"Update Correction for {uploaded_image_name}"):
            if corrected_plant_input:
                update_history(uploaded_image_name, corrected_plant_input)
                # Refresh the uploaded images list
                st.session_state.uploaded_images.append(uploaded_image_name)
        return  # Skip processing since the image already exists

    # If it doesn't exist, process the image
    results = backend.process_image(image_data, uploaded_image_name)  # Call your backend function here
    
    if results:  # Check if results are not empty
        # Find the best match based on confidence
        best_match = max(results, key=lambda x: x['Confidence'])
        identified_plant = best_match['Identified Plant']
        confidence = best_match['Confidence']

        # Display uploaded image and cropped image side by side
        col1, col2 = st.columns(2)
        with col1:
            st.image(image_data, caption="Uploaded Image", use_column_width=True)
        with col2:
            cropped_image = best_match['Cropped Image']
            st.image(cropped_image, caption="Cropped Image", use_column_width=True)

        # Display identification result
        st.write(f"Identified Plant: {identified_plant} (Confidence: {confidence:.2f})")

        # Insert new record into MongoDB
        collection.insert_one({
            'uploaded_image': uploaded_image_name,
            'identified_plant': identified_plant,
            'corrected_plant': None,
            'confidence': confidence
        })
        st.success(f"Inserted new entry for {uploaded_image_name} in the database.")

        # Text input for corrected plant name
        corrected_plant = st.text_input(f"Corrected Plant for {uploaded_image_name}:", key=f"{uploaded_image_name}_correction")

        # Button to save correction
        if st.button(f"Update Correction for {uploaded_image_name}"):
            if corrected_plant:
                update_history(uploaded_image_name, corrected_plant)
                # Refresh the uploaded images list
                st.session_state.uploaded_images.append(uploaded_image_name)
    else:
        st.warning("No results found for the uploaded image.")

# File uploader for images or zip files
st.sidebar.header("Upload & History")
uploaded_files = st.sidebar.file_uploader("Upload images or a folder (zip)", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=False)

# Display upload history in the sidebar
st.sidebar.subheader("Upload History")
history = fetch_history()

if history:
    # Create DataFrame from fetched history
    history_df = pd.DataFrame(history)
    columns_to_display = ['uploaded_image', 'identified_plant', 'corrected_plant', 'confidence']
    st.sidebar.dataframe(history_df[columns_to_display])

# Process uploaded files
if uploaded_files:
    # Clear previous uploaded images and data
    st.session_state.uploaded_images.clear()
    st.session_state.current_data.clear()
    
    if uploaded_files.name.endswith('.zip'):
        handle_folder_upload(uploaded_files)
    else:
        process_image(uploaded_files.read(), uploaded_files.name)

# Show uploaded images and their details for the current session only
if st.session_state.uploaded_images:
    st.subheader("Uploaded Images and Details")
    for img_name in st.session_state.uploaded_images:
        existing_entry = collection.find_one({'uploaded_image': img_name})
        if existing_entry:
            st.write(f"Image: {img_name}")
            st.write(f"Identified Plant: {existing_entry['identified_plant']}")
            st.write(f"Corrected Plant: {existing_entry.get('corrected_plant', 'None')}")
            st.write(f"Confidence: {existing_entry['confidence']:.2f}")
