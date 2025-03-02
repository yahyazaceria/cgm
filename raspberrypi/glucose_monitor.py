import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time
import tflite_runtime.interpreter as tflite
import numpy as np
import requests
from datetime import datetime
from PIL import Image

# GPIO Setup
LED_PIN = 23  # LED pin
BUTTON_PIN = 17  # Button pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def setup_camera():
    camera = Picamera2()
    camera.start()
    time.sleep(1)  # Allow camera to initialize
    return camera

def capture_image(camera):
    # Turn on LED
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(1)  # Wait for LED to stabilize
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f'captured_image_{timestamp}.jpg'
    
    try:
        # Capture image
        camera.capture_file(image_path)
        print("Image captured successfully!")
        
        # Read the image for processing
        frame = camera.capture_array()
        
    finally:
        # Turn off LED
        GPIO.output(LED_PIN, GPIO.LOW)
    
    return image_path, frame

def load_model():
    interpreter = tflite.Interpreter(model_path='glucose_model.tflite')
    interpreter.allocate_tensors()
    return interpreter

def process_image(frame):
    interpreter = load_model()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Convert frame to PIL Image and resize
    image = Image.fromarray(frame)
    resized = image.resize((224, 224))
    
    # Convert to numpy array and normalize
    img_array = np.array(resized)
    
    # Remove alpha channel if it exists
    if img_array.shape[-1] == 4:  # If image has RGBA channels
        img_array = img_array[:, :, :3]  # Keep only RGB
    
    # Make sure we have 3 channels (RGB)
    if len(img_array.shape) == 2:  # If grayscale
        img_array = np.stack((img_array,)*3, axis=-1)
    
    # Normalize
    normalized = img_array / 255.0
    input_data = np.expand_dims(normalized, axis=0).astype(np.float32)
    
    # Print shapes for debugging
    print(f"Input shape: {input_data.shape}")
    print(f"Expected shape: {input_details[0]['shape']}")
    
    # Make prediction
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])
    
    # Scale the prediction to realistic glucose levels (70-300 mg/dL)
    raw_prediction = float(prediction[0][0])
    glucose_level = (raw_prediction * 230) + 70  # Scales 0-1 to 70-300 mg/dL
    print(f"Glucose level measured: {glucose_level:.1f} mg/dL")
    return glucose_level

def send_to_webapp(glucose_level):
    # Use your computer's IP address instead of localhost
    url = 'http://192.168.4.151:3000/api/readings'  # Replace YOUR_COMPUTER_IP with actual IP
    data = {
        'value': glucose_level,
        'deviceId': 'raspberry_pi_1'
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print("Data sent to web app successfully!")
        print(f"View your readings at: http://192.168.4.151:3000")  # Replace YOUR_COMPUTER_IP
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to web app: {e}")

def cleanup():
    GPIO.cleanup()

def main():
    try:
        camera = setup_camera()
        print("System ready! Press the button to capture an image...")
        
        while True:
            # Wait for button press
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                try:
                    # Capture and process image
                    image_path, frame = capture_image(camera)
                    glucose_level = process_image(frame)
                    send_to_webapp(glucose_level)
                    
                    # Wait to avoid multiple captures
                    time.sleep(2)
                except Exception as e:
                    print(f"Error during capture/processing: {e}")
                
            time.sleep(0.1)  # Small delay to prevent CPU overuse
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    finally:
        cleanup()

if __name__ == "__main__":
    main() 