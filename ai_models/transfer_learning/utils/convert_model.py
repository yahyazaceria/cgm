import tensorflow as tf

# Load your model
model = tf.keras.models.load_model('glucose_model.h5')

# Convert to TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Save the TFLite model
with open('glucose_model.tflite', 'wb') as f:
    f.write(tflite_model)

# Print model info
interpreter = tf.lite.Interpreter(model_content=tflite_model)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
print("Expected input shape:", input_details[0]['shape'])
print("Model converted successfully!") 