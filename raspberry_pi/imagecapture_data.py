from picamera2 import Picamera2
from gpiozero import Button, LED
from datetime import datetime
from time import sleep
import pandas as pd
import os
from signal import signal, SIGTERM, SIGHUP, pause
from rpi_lcd import LCD

# Initialize camera and components
camera = Picamera2()
button = Button(17)  # Assuming button is connected to GPIO 17
laser = LED(23)  # Assuming laser is connected to GPIO 23
lcd = LCD()  # Initialize the LCD

def safe_exit(signum, frame):
    exit(1)

signal(SIGTERM, safe_exit)
signal(SIGHUP, safe_exit)

# Global variables
spreadsheet_path = "/home/zaceriafamily/dev/ACSEF/cgm/data/photos_data.csv"
img_directory = "/home/zaceriafamily/dev/ACSEF/cgm/data/"
filename = ''
patient_id = ''

# Function to initialize or load the CSV file
def init_csv():
    if os.path.exists(spreadsheet_path):
        if os.stat(spreadsheet_path).st_size > 0:
            df = pd.read_csv(spreadsheet_path)
        else:
            df = pd.DataFrame(columns=['Timestamp', 'Patient ID', 'Filename', 'Glucose Level', 'CGM Value'])
    else:
        df = pd.DataFrame(columns=['Timestamp', 'Patient ID', 'Filename', 'Glucose Level', 'CGM Value'])
        df.to_csv(spreadsheet_path, index=False)
    return df

# Initialize or load the CSV
df = init_csv()

# Function to take a photo and control the laser
def take_photo():
    global filename
    global patient_id

    # Ask for the patient ID
    patient_id = input("Enter Patient ID (e.g. 1 for Mom, 2 for Dad): ")

    # Generate a unique filename using the current timestamp and patient ID
    now = datetime.now()
    filename = f"{patient_id}_{now.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"

    # Turn on the laser
    laser.on()
    print("Turned on laser")
    
    # Start camera preview and capture image with error handling
    try:
        camera.start_preview(alpha=190)
        print("Started camera preview")
        camera.start()
        sleep(1)  # Allow camera to stabilize
        camera.capture_file(f"{img_directory}/{filename}")
        print("Captured image")
    except Exception as e:
        print(f"Error capturing image: {e}")
    finally:
        camera.stop_preview()

    # Turn off the laser after capturing the photo
    laser.off()
    print("Laser turned off")

    # Capture glucose level input, confirm it, and save it
    try:
        glucose_level = input_glucose_level()
        cgm_value = input_cgm_value()  # Capture CGM value after glucose level
        save_to_csv(now, patient_id, filename, glucose_level, cgm_value)
    except KeyboardInterrupt:
        pass
    finally:
        lcd.clear()

# Function to handle glucose level input once, display it for confirmation, and wait for user to confirm
def input_glucose_level():
    while True:
        lcd.clear()
        lcd.text("Enter glucose:", 1)
        glucose_level = input("Enter glucose level (press Enter to submit): ")

        # Display confirmation message on LCD
        lcd.clear()
        lcd.text(f"Confirm: {glucose_level}", 1)
        confirm = input("Press Enter to confirm, any other key to re-enter: ")
        if confirm == "":  # Confirm the input when Enter is pressed
            return glucose_level
        else:
            print("Input not confirmed. Please re-enter the glucose level.")
            lcd.clear()
            lcd.text("Re-enter glucose:", 1)

# Function to handle CGM value input
def input_cgm_value():
    lcd.clear()
    lcd.text("Enter CGM value:", 1)
    cgm_value = input("Enter wearable CGM value (press Enter to submit): ")
    lcd.clear()
    lcd.text(f"CGM Value: {cgm_value}", 1)
    print(f"CGM value entered: {cgm_value}")
    return cgm_value

# Function to save the captured image details to the existing CSV file
def save_to_csv(timestamp, patient_id, image_filename, glucose_level, cgm_value):
    new_row = {
        'Timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'Patient ID': patient_id,
        'Filename': image_filename,
        'Glucose Level': glucose_level,
        'CGM Value': cgm_value
    }
    
    global df
    df = df.append(new_row, ignore_index=True)

    try:
        df.to_csv(spreadsheet_path, index=False)
        print(f"Data saved to CSV: {spreadsheet_path}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# Bind the button press event to take the photo
lcd.text("Ready!", 1)
button.when_pressed = take_photo

# Keep the script running
while True:
    pause()

