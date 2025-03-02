import tensorflow as tf
from tensorflow.keras import layers, models
import pandas as pd
import numpy as np
from PIL import Image
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_absolute_percentage_error
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
import pathlib

# Image parameters
IMG_SIZE = (224, 224)
BATCH_SIZE = 32

# Load and prepare data
def load_image(image_path):
    try:
        # Convert string to bytes for tf.io.read_file
        if isinstance(image_path, str):
            image_path = image_path.encode()
            
        img = tf.io.read_file(image_path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, IMG_SIZE)
        img = tf.cast(img, tf.float32) / 255.0  # Normalize to [0,1]
        return img
    except Exception as e:
        print(f"Error loading image {image_path}: {str(e)}")
        raise

def prepare_dataset():
    # Load data from CSV
    df = pd.read_csv('data/photos_data.csv')
    
    # Rename columns
    df = df.rename(columns={'Filename': 'image_path', 'Glucose Level': 'glucose_level'})
    
    # Add the full path to the images
    data_dir = pathlib.Path('data/photos')  # Adjust this to your image directory
    df['image_path'] = df['image_path'].apply(lambda x: str(data_dir / x))
    
    # Verify files exist
    missing_files = df[~df['image_path'].apply(lambda x: pathlib.Path(x).exists())]['image_path']
    if len(missing_files) > 0:
        print("\nWARNING: Following image files are missing:")
        print(missing_files.tolist())
        print("\nPlease check the image paths and ensure all files exist.")
        raise FileNotFoundError("Missing image files")
    
    # Split into train/validation sets
    train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)
    
    # Debug info
    print(f"\nFirst few image paths:")
    print(df['image_path'].head())
    print(f"\nTotal images found: {len(df)}")
    
    # Create datasets
    train_ds = tf.data.Dataset.from_tensor_slices((
        train_df['image_path'].values,
        train_df['glucose_level'].values
    ))
    
    val_ds = tf.data.Dataset.from_tensor_slices((
        val_df['image_path'].values,
        val_df['glucose_level'].values
    ))
    
    # Map and configure datasets
    train_ds = train_ds.map(lambda x, y: (load_image(x), y))
    val_ds = val_ds.map(lambda x, y: (load_image(x), y))
    
    train_ds = train_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    
    return train_ds, val_ds

# Data augmentation
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip('horizontal'),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.2),
])

# Create the base model from pretrained MobileNetV2
base_model = tf.keras.applications.MobileNetV2(
    input_shape=IMG_SIZE + (3,),
    include_top=False,
    weights='imagenet'
)

# Freeze the base model
base_model.trainable = False

# Create the model
def create_model():
    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    
    # Data augmentation
    x = data_augmentation(inputs)
    
    # Preprocess input
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    
    # Base model
    x = base_model(x, training=False)
    
    # Global pooling and dropout
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    
    # Regression head
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dense(64, activation='relu')(x)
    outputs = layers.Dense(1)(x)
    
    return tf.keras.Model(inputs, outputs)

# Training
def train_model():
    # Prepare datasets
    train_ds, val_ds = prepare_dataset()
    
    # Create and compile model
    model = create_model()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-4),
        loss='huber',
        metrics=['mae', 'mse']
    )
    
    # Initial training
    print("Initial training...")
    history = model.fit(
        train_ds,
        epochs=10,
        validation_data=val_ds,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)
        ]
    )
    
    # Fine tuning
    print("Fine-tuning...")
    base_model.trainable = True
    
    # Freeze first 100 layers
    for layer in base_model.layers[:100]:
        layer.trainable = False
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss='huber',
        metrics=['mae', 'mse']
    )
    
    history_fine = model.fit(
        train_ds,
        epochs=10,
        validation_data=val_ds,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)
        ]
    )
    
    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model.save(f'glucose_model_{timestamp}.h5')
    
    # Plot training results
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history.history['mae'] + history_fine.history['mae'])
    plt.plot(history.history['val_mae'] + history_fine.history['val_mae'])
    plt.title('Model MAE')
    plt.ylabel('MAE')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'])
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'] + history_fine.history['loss'])
    plt.plot(history.history['val_loss'] + history_fine.history['val_loss'])
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'])
    
    plt.tight_layout()
    plt.savefig(f'training_history_{timestamp}.png')
    
    return model

if __name__ == '__main__':
    model = train_model()

# Print dataset info
print(f"\nTotal images: {len(df)}")
print("\nGlucose Level Statistics:")
print(df['glucose_level'].describe())

# Print some debug info
print("CSV contents:")
print(df.head())
print("\nTotal images to process:", len(df))

# Update the image loading code
X = np.array([load_image(f) for f in df['image_path']])
y = np.array(df['glucose_level'])

# Normalize glucose levels to 0-1 range for training
y_min, y_max = 70, 300  # Expected glucose range
y_normalized = (y - y_min) / (y_max - y_min)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y_normalized, test_size=0.2, random_state=42)
print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")

# Enhanced model architecture
model = models.Sequential([
    # First conv block with more filters
    layers.Conv2D(64, (3, 3), activation='relu', padding='same', input_shape=(224, 224, 3)),
    layers.BatchNormalization(),
    layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.3),
    
    # Second conv block
    layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.3),
    
    # Third conv block
    layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.3),
    
    # Dense layers
    layers.Flatten(),
    layers.Dense(512, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.5),
    layers.Dense(256, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.5),
    layers.Dense(1, activation='linear')
])

# Compile with reduced learning rate
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.00005),
    loss='huber',  # More robust to outliers
    metrics=['mae']
)

# Add more callbacks
callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=15,
        restore_best_weights=True
    ),
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=0.00001
    )
]

# Train for longer
history = model.fit(
    X_train, y_train,
    epochs=200,
    batch_size=16,
    validation_data=(X_test, y_test),
    callbacks=callbacks,
    verbose=1
)

# Save model
model.save('glucose_model.h5')

# Calculate predictions
y_pred_norm = model.predict(X_test)
y_pred = (y_pred_norm * (y_max - y_min)) + y_min
y_true = (y_test * (y_max - y_min)) + y_min

# Calculate additional metrics
mape = mean_absolute_percentage_error(y_true, y_pred) * 100
accuracy = 100 - mape

print("\n=== Final Model Performance ===")
print(f"Mean Absolute Error: {mae:.1f} mg/dL")
print(f"Mean Absolute Percentage Error: {mape:.1f}%")
print(f"Accuracy: {accuracy:.1f}%")
print(f"R² Score: {r2:.3f}")
print(f"Average Error Range: ±{mae:.1f} mg/dL")

# Create additional visualizations
plt.figure(figsize=(20, 10))

# Original three plots
plt.subplot(2, 3, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss Over Time')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(2, 3, 2)
plt.plot(history.history['mae'], label='Training MAE')
plt.plot(history.history['val_mae'], label='Validation MAE')
plt.title('Model MAE Over Time')
plt.xlabel('Epoch')
plt.ylabel('MAE')
plt.legend()

plt.subplot(2, 3, 3)
plt.scatter(y_true, y_pred, alpha=0.5)
plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
plt.title('Predictions vs Actual')
plt.xlabel('Actual Glucose Level (mg/dL)')
plt.ylabel('Predicted Glucose Level (mg/dL)')

# Error distribution
plt.subplot(2, 3, 4)
errors = y_pred - y_true
sns.histplot(errors, kde=True)
plt.title('Error Distribution')
plt.xlabel('Prediction Error (mg/dL)')

# Learning rate over time
plt.subplot(2, 3, 5)
plt.plot(history.history['lr'] if 'lr' in history.history else [])
plt.title('Learning Rate Over Time')
plt.xlabel('Epoch')
plt.ylabel('Learning Rate')

plt.tight_layout()

# Save plots
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
plt.savefig(f'training_metrics_{timestamp}.png')
print(f"\nTraining plots saved as training_metrics_{timestamp}.png")

# Print example predictions
print("\nExample Predictions vs Actual:")
for i in range(min(5, len(y_test))):
    pred = float(y_pred[i])  # Convert numpy float to Python float
    true = float(y_true[i])  # Convert numpy float to Python float
    print(f"Predicted: {pred:.1f} mg/dL, Actual: {true:.1f} mg/dL") 