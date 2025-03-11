import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time
import tflite_runtime.interpreter as tflite
import numpy as np
import requests
from datetime import datetime
from PIL import Image
import os

# GPIO Setup
LED_PIN = 23  # LED pin
BUTTON_PIN = 17  # Button pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Model parameters
IMG_SIZE = (224, 224)
Y_MIN = 70   # Minimum glucose level
Y_MAX = 300  # Maximum glucose level

def setup_camera():
    camera = Picamera2()
    camera.start()
    time.sleep(1)  # Allow camera to initialize
    return camera

def capture_image(camera):
    # Turn on LED
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(1)  # Wait for LED to stabilize
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f'/home/pi/glucose_monitor/captured_images/captured_image_{timestamp}.jpg'
    
    try:
        # Capture image
        camera.capture_file(image_path)
        print(f"Image captured and saved to: {image_path}")
        
        # Read the image for processing
        frame = camera.capture_array()
        
    finally:
        # Turn off LED
        GPIO.output(LED_PIN, GPIO.LOW)
    
    return image_path, frame

def preprocess_image(frame):
    """Preprocess image to match model requirements"""
    # Convert to PIL Image and resize
    image = Image.fromarray(frame)
    image = image.resize(IMG_SIZE)
    
    # Convert to numpy array and normalize
    img_array = np.array(image)
    
    # Ensure 3 channels (RGB)
    if len(img_array.shape) == 2:  # If grayscale
        img_array = np.stack((img_array,)*3, axis=-1)
    elif img_array.shape[-1] == 4:  # If RGBA
        img_array = img_array[:, :, :3]
    
    # Normalize to [0,1]
    img_array = img_array.astype(np.float32) / 255.0
    
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def load_model():
    model_path = '/home/pi/glucose_monitor/models/glucose_model.tflite'
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter

def process_image(frame):
    interpreter = load_model()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Preprocess image
    input_data = preprocess_image(frame)
    
    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], input_data)
    
    # Run inference
    interpreter.invoke()
    
    # Get prediction
    prediction = interpreter.get_tensor(output_details[0]['index'])
    
    # Denormalize prediction
    glucose_level = float(prediction[0][0]) * (Y_MAX - Y_MIN) + Y_MIN
    
    print(f"Glucose level measured: {glucose_level:.1f} mg/dL")
    return glucose_level

def send_to_webapp(glucose_level):
    url = 'https://your-vercel-app.vercel.app/api/readings'  # Update with your Vercel app URL
    data = {
        'value': glucose_level,
        'deviceId': 'raspberry_pi_1'
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print("Data sent to web app successfully!")
        print(f"View your readings at: {url}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to web app: {e}")

def cleanup():
    GPIO.cleanup()

def main():
    # Create necessary directories
    os.makedirs('/home/pi/glucose_monitor/captured_images', exist_ok=True)
    os.makedirs('/home/pi/glucose_monitor/models', exist_ok=True)
    
    try:
        camera = setup_camera()
        print("System ready! Press the button to capture an image...")
        
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                try:
                    image_path, frame = capture_image(camera)
                    glucose_level = process_image(frame)
                    send_to_webapp(glucose_level)
                    time.sleep(2)  # Debounce
                except Exception as e:
                    print(f"Error during capture/processing: {e}")
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    finally:
        cleanup()

if __name__ == "__main__":
    main() 