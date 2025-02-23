import time
from picamera2 import Picamera2
import tensorflow as tf
from PIL import Image
import numpy as np
from RPLCD.i2c import CharLCD
import socketio
import os

class GlucoseMonitor:
    def __init__(self, model_path, server_url):
        # Initialize camera
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_preview_configuration())
        self.camera.start()
        
        # Initialize LCD
        self.lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
        
        # Load trained model
        self.model = tf.keras.models.load_model(model_path)
        
        # Initialize Socket.IO client
        self.sio = socketio.Client()
        self.server_url = server_url
        self.connect_to_server()
    
    def connect_to_server(self):
        try:
            self.sio.connect(self.server_url)
        except Exception as e:
            print(f"Could not connect to server: {e}")
    
    def process_image(self, image):
        # Preprocess image for model
        image = Image.fromarray(image)
        image = image.resize((224, 224))
        image = np.array(image) / 255.0
        image = np.expand_dims(image, axis=0)
        return image
    
    def measure_glucose(self):
        try:
            # Capture image
            image = self.camera.capture_array()
            
            # Process image and get prediction
            processed_image = self.process_image(image)
            glucose_level = float(self.model.predict(processed_image)[0])
            
            # Display on LCD
            self.lcd.clear()
            self.lcd.write_string(f'Glucose Level:')
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f'{glucose_level:.1f} mg/dL')
            
            # Send to server
            try:
                self.sio.emit('new_reading', {
                    'glucose_level': glucose_level
                })
            except Exception as e:
                print(f"Error sending to server: {e}")
            
            return glucose_level
            
        except Exception as e:
            print(f"Error measuring glucose: {e}")
            self.lcd.clear()
            self.lcd.write_string('Error occurred')
            return None

def main():
    monitor = GlucoseMonitor(
        model_path='path/to/glucose_model.h5',
        server_url='http://your_server:5000'
    )
    
    while True:
        monitor.measure_glucose()
        time.sleep(300)  # Take reading every 5 minutes

if __name__ == "__main__":
    main() 