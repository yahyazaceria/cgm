import tensorflow as tf
from tensorflow.keras import layers, models
import pandas as pd
import numpy as np
import os
import pathlib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from datetime import datetime
import sys

# -------------------
# Global parameters
# -------------------
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
Y_MIN = 70   # Minimum glucose level
Y_MAX = 300  # Maximum glucose level
EPOCHS_HEAD = 30   # Initial training epochs for the head
EPOCHS_FINE = 10   # Additional epochs for fine-tuning

# -------------------
# Data Augmentation
# -------------------
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip('horizontal'),
    layers.RandomRotation(0.3),
    layers.RandomZoom(0.2),
    layers.RandomTranslation(0.2, 0.2),
    layers.GaussianNoise(0.1),
], name="data_augmentation")

# -------------------
# Utility Functions
# -------------------
def load_image(image_path):
    """Load and preprocess a single image."""
    try:
        img = tf.io.read_file(image_path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, IMG_SIZE)
        img = tf.cast(img, tf.float32) / 255.0  # normalize to [0,1]
        return img
    except Exception as e:
        print(f"Error loading image {image_path}: {str(e)}")
        raise

def prepare_dataset(csv_path, images_dir):
    """Read CSV, verify image files exist, and return a DataFrame."""
    df = pd.read_csv(csv_path)
    # Rename columns for convenience
    df = df.rename(columns={
        'Filename': 'image_path', 
        'Glucose Level': 'glucose_level',
        'CGM Value': 'cgm_value'  # rename for clarity
    })
    images_dir = pathlib.Path(images_dir)
    if not images_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {images_dir}")
    available_images = set(f.name for f in images_dir.glob('*.jpg'))
    df['image_path'] = df['image_path'].apply(lambda x: str(images_dir / x))
    valid_mask = df['image_path'].apply(lambda x: pathlib.Path(x).name in available_images)
    df = df[valid_mask].reset_index(drop=True)
    print(f"Found {len(df)} valid images in CSV after filtering missing files.")
    return df

def augment_dataset(images, labels, num_aug=5):
    """Augment each image multiple times."""
    aug_images, aug_labels = [], []
    for image, label in zip(images, labels):
        # Include the original image
        aug_images.append(image)
        aug_labels.append(label)
        for _ in range(num_aug):
            aug_img = data_augmentation(tf.expand_dims(image, 0))[0]
            aug_images.append(aug_img)
            aug_labels.append(label)
    return np.array(aug_images), np.array(aug_labels)

def calculate_mard(y_true, y_pred):
    """Calculate Mean Absolute Relative Difference (MARD)."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.mean(np.abs(y_pred - y_true) / y_true) * 100

def calculate_clinical_accuracy(y_true, y_pred, thresholds=[5, 10, 15]):
    """
    Calculate the percentage of predictions within a given relative error.
    Also includes an absolute threshold (e.g. within ±20 mg/dL).
    """
    total = len(y_true)
    accuracies = {}
    abs_diff = np.abs(y_pred - y_true)
    percent_errors = (abs_diff / y_true) * 100
    for t in thresholds:
        accuracies[f"within_{t}%"] = (np.sum(percent_errors <= t) / total) * 100
    accuracies["within_20mg"] = (np.sum(abs_diff <= 20) / total) * 100
    return accuracies

# -------------------
# Custom Callback
# -------------------
class MetricsCallback(tf.keras.callbacks.Callback):
    """
    Tracks MARD, MAE, and clinical accuracy on train/val/test each epoch.
    """
    def __init__(self, train_data, val_data, test_data, y_min, y_max):
        super().__init__()
        self.train_images, self.train_labels = train_data
        self.val_images, self.val_labels = val_data
        self.test_images, self.test_labels = test_data
        self.y_min = y_min
        self.y_max = y_max
        self.history = {
            "train_mard": [], "val_mard": [], "test_mard": [],
            "train_mae": [], "val_mae": [], "test_mae": [],
            "train_acc": [], "val_acc": [], "test_acc": []
        }
    
    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        train_mard, train_acc, train_mae = self.evaluate_set(self.train_images, self.train_labels)
        val_mard, val_acc, val_mae = self.evaluate_set(self.val_images, self.val_labels)
        test_mard, test_acc, test_mae = self.evaluate_set(self.test_images, self.test_labels)
        self.history["train_mard"].append(train_mard)
        self.history["val_mard"].append(val_mard)
        self.history["test_mard"].append(test_mard)
        self.history["train_mae"].append(train_mae)
        self.history["val_mae"].append(val_mae)
        self.history["test_mae"].append(test_mae)
        self.history["train_acc"].append(train_acc)
        self.history["val_acc"].append(val_acc)
        self.history["test_acc"].append(test_acc)
        print(f"\nEpoch {epoch+1}:")
        print(f"Train MARD: {train_mard:.1f}% | Val MARD: {val_mard:.1f}% | Test MARD: {test_mard:.1f}%")
        print(f"Train MAE: {train_mae:.1f} | Val MAE: {val_mae:.1f} | Test MAE: {test_mae:.1f}")
        print("Train Acc:", train_acc)
        print("Val Acc:", val_acc)
        print("Test Acc:", test_acc)
    
    def evaluate_set(self, images, labels):
        y_pred_norm = self.model.predict(images, verbose=0)
        y_pred_norm = np.squeeze(y_pred_norm)
        y_pred = y_pred_norm * (self.y_max - self.y_min) + self.y_min
        y_true = labels * (self.y_max - self.y_min) + self.y_min
        mard = calculate_mard(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        acc = calculate_clinical_accuracy(y_true, y_pred)
        return mard, acc, mae

# -------------------
# Model Definition
# -------------------
def create_model():
    # Create the base model (ResNet50)
    base_model = tf.keras.applications.ResNet50(
        weights='imagenet',
        include_top=False,
        input_shape=IMG_SIZE + (3,)
    )
    base_model.trainable = False  # initially freeze base model
    
    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = tf.keras.applications.resnet50.preprocess_input(x)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(512, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(1, activation='linear')(x)
    model = tf.keras.Model(inputs, outputs)
    # Save reference to the base model for later fine-tuning
    model.base_model = base_model
    return model

# -------------------
# Plotting Functions
# -------------------
def plot_metrics(callback_history, timestamp):
    num_epochs = len(callback_history["train_mard"])
    epochs = range(1, num_epochs + 1)
    fig, axs = plt.subplots(3, 2, figsize=(15,15))
    axs = axs.flatten()
    if "loss" in callback_history and "val_loss" in callback_history:
        axs[0].plot(epochs, callback_history["loss"], label='Train Loss')
        axs[0].plot(epochs, callback_history["val_loss"], label='Val Loss')
        axs[0].set_title("Loss Over Epochs")
        axs[0].set_xlabel("Epoch")
        axs[0].set_ylabel("Loss")
        axs[0].legend()
    axs[1].plot(epochs, callback_history["train_mard"], label='Train MARD')
    axs[1].plot(epochs, callback_history["val_mard"], label='Val MARD')
    axs[1].plot(epochs, callback_history["test_mard"], label='Test MARD')
    axs[1].set_title("MARD Over Epochs")
    axs[1].set_xlabel("Epoch")
    axs[1].set_ylabel("MARD (%)")
    axs[1].legend()
    axs[2].plot(epochs, callback_history["train_mae"], label='Train MAE')
    axs[2].plot(epochs, callback_history["val_mae"], label='Val MAE')
    axs[2].plot(epochs, callback_history["test_mae"], label='Test MAE')
    axs[2].set_title("MAE Over Epochs")
    axs[2].set_xlabel("Epoch")
    axs[2].set_ylabel("MAE (mg/dL)")
    axs[2].legend()
    train_acc_15 = [acc["within_15%"] for acc in callback_history["train_acc"]]
    val_acc_15 = [acc["within_15%"] for acc in callback_history["val_acc"]]
    test_acc_15 = [acc["within_15%"] for acc in callback_history["test_acc"]]
    axs[3].plot(epochs, train_acc_15, label='Train Acc (±15%)')
    axs[3].plot(epochs, val_acc_15, label='Val Acc (±15%)')
    axs[3].plot(epochs, test_acc_15, label='Test Acc (±15%)')
    axs[3].set_title("Clinical Accuracy (±15%)")
    axs[3].set_xlabel("Epoch")
    axs[3].set_ylabel("Accuracy (%)")
    axs[3].legend()
    train_acc_10 = [acc["within_10%"] for acc in callback_history["train_acc"]]
    val_acc_10 = [acc["within_10%"] for acc in callback_history["val_acc"]]
    test_acc_10 = [acc["within_10%"] for acc in callback_history["test_acc"]]
    axs[4].plot(epochs, train_acc_10, label='Train Acc (±10%)')
    axs[4].plot(epochs, val_acc_10, label='Val Acc (±10%)')
    axs[4].plot(epochs, test_acc_10, label='Test Acc (±10%)')
    axs[4].set_title("Clinical Accuracy (±10%)")
    axs[4].set_xlabel("Epoch")
    axs[4].set_ylabel("Accuracy (%)")
    axs[4].legend()
    train_acc_5 = [acc["within_5%"] for acc in callback_history["train_acc"]]
    val_acc_5 = [acc["within_5%"] for acc in callback_history["val_acc"]]
    test_acc_5 = [acc["within_5%"] for acc in callback_history["test_acc"]]
    axs[5].plot(epochs, train_acc_5, label='Train Acc (±5%)')
    axs[5].plot(epochs, val_acc_5, label='Val Acc (±5%)')
    axs[5].plot(epochs, test_acc_5, label='Test Acc (±5%)')
    axs[5].set_title("Clinical Accuracy (±5%)")
    axs[5].set_xlabel("Epoch")
    axs[5].set_ylabel("Accuracy (%)")
    axs[5].legend()
    plt.tight_layout()
    plt.savefig(f"metrics_over_time_{timestamp}.png")
    plt.show()

def plot_predictions(model, X, y_true_norm, df_test, y_min, y_max):
    # 1) Predictions vs. Actual
    y_pred_norm = model.predict(X)
    y_pred_norm = np.squeeze(y_pred_norm)
    y_pred = y_pred_norm * (y_max - y_min) + y_min
    y_true = y_true_norm * (y_max - y_min) + y_min
    plt.figure(figsize=(8,6))
    plt.scatter(y_true, y_pred, alpha=0.5, label='Predicted')
    plt.plot([y_true.min(), y_true.max()],
             [y_true.min(), y_true.max()], 'r--', label='Ideal')
    plt.xlabel("Actual Glucose (mg/dL)")
    plt.ylabel("Predicted Glucose (mg/dL)")
    plt.title(f"Predictions vs Actual (MARD: {calculate_mard(y_true, y_pred):.1f}%)")
    plt.legend()
    plt.savefig("predicted_vs_actual.png")
    plt.show()
    # 2) Error Distribution
    errors = y_pred - y_true
    plt.figure(figsize=(8,6))
    sns.histplot(errors, kde=True)
    plt.xlabel("Prediction Error (mg/dL)")
    plt.title("Error Distribution")
    plt.savefig("error_distribution.png")
    plt.show()
    # 3) Accuracy vs. Error Threshold
    percent_errors = np.abs((y_pred - y_true) / y_true) * 100
    thresholds = np.arange(0, 51, 5)
    accuracies = [(np.sum(percent_errors <= t) / len(y_true)) * 100 for t in thresholds]
    plt.figure(figsize=(8,6))
    plt.plot(thresholds, accuracies, marker='o')
    plt.xlabel("Error Threshold (%)")
    plt.ylabel("Accuracy (%)")
    plt.title("Clinical Accuracy across Different Error Thresholds")
    plt.savefig("accuracy_thresholds.png")
    plt.show()
    # 4) Compare CGM vs. Model vs. Actual over Time
    df_test_sorted = df_test.copy()
    df_test_sorted['Timestamp'] = pd.to_datetime(df_test_sorted['Timestamp'])
    df_test_sorted.sort_values('Timestamp', inplace=True)
    df_test_sorted.reset_index(drop=True, inplace=True)
    actual_values = df_test_sorted['glucose_level'].values
    cgm_values = df_test_sorted['cgm_value'].values
    timestamps = df_test_sorted['Timestamp'].values
    sorted_image_paths = df_test_sorted['image_path'].values
    sorted_images = np.array([load_image(p) for p in sorted_image_paths])
    sorted_pred_norm = model.predict(sorted_images)
    sorted_pred = np.squeeze(sorted_pred_norm) * (y_max - y_min) + y_min
    plt.figure(figsize=(10,6))
    plt.plot(timestamps, actual_values, 'o-', label='Actual (Lab) Glucose')
    plt.plot(timestamps, cgm_values, 's-', label='CGM Value')
    plt.plot(timestamps, sorted_pred, 'd-', label='Model Prediction')
    plt.title("CGM vs. Model vs. Actual Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Glucose (mg/dL)")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("compare_cgm_vs_model.png")
    plt.show()

# -------------------
# Main Training
# -------------------
def train_model():
    df = prepare_dataset("../../data/photos_data.csv", "../../data/images")
    train_df, temp_df = train_test_split(df, test_size=0.4, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    X_train = np.array([load_image(p) for p in train_df['image_path']])
    X_val   = np.array([load_image(p) for p in val_df['image_path']])
    X_test  = np.array([load_image(p) for p in test_df['image_path']])
    y_train = np.array(train_df['glucose_level'])
    y_val   = np.array(val_df['glucose_level'])
    y_test  = np.array(test_df['glucose_level'])
    print("Augmenting training data...")
    X_train, y_train = augment_dataset(X_train, y_train, num_aug=5)
    print("Augmenting validation data...")
    X_val, y_val = augment_dataset(X_val, y_val, num_aug=2)
    y_train_norm = (y_train - Y_MIN) / (Y_MAX - Y_MIN)
    y_val_norm   = (y_val - Y_MIN) / (Y_MAX - Y_MIN)
    y_test_norm  = (y_test - Y_MIN) / (Y_MAX - Y_MIN)
    model = create_model()
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
                  loss='huber', metrics=['mae'])
    metrics_cb = MetricsCallback((X_train, y_train_norm),
                                 (X_val, y_val_norm),
                                 (X_test, y_test_norm),
                                 Y_MIN, Y_MAX)
    callbacks = [
        metrics_cb,
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6),
    ]
    print("Training head (frozen base) ...")
    history = model.fit(X_train, y_train_norm,
                        validation_data=(X_val, y_val_norm),
                        epochs=EPOCHS_HEAD,
                        batch_size=16,
                        callbacks=callbacks,
                        verbose=1)
    # Fine-tuning phase: unfreeze last 10 layers of the base model
    print("\nStarting fine-tuning...")
    model.base_model.trainable = True
    for layer in model.base_model.layers[:-10]:
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
                  loss='huber', metrics=['mae'])
    history_fine = model.fit(X_train, y_train_norm,
        validation_data=(X_val, y_val_norm),
                             epochs=EPOCHS_FINE,
        batch_size=16,
        callbacks=callbacks,
                             verbose=1)
    # Evaluate final model
    y_pred_norm = model.predict(X_test)
    y_pred_norm = np.squeeze(y_pred_norm)
    y_pred = y_pred_norm * (Y_MAX - Y_MIN) + Y_MIN
    y_true = y_test_norm * (Y_MAX - Y_MIN) + Y_MIN
    final_mard = calculate_mard(y_true, y_pred)
    final_mae = mean_absolute_error(y_true, y_pred)
    final_acc = calculate_clinical_accuracy(y_true, y_pred)
    print("\n=== Final Model Performance ===")
    print(f"MARD: {final_mard:.1f}%")
    print(f"Mean Absolute Error: {final_mae:.1f} mg/dL")
    print("Clinical Accuracy Metrics:", final_acc)
    combined_history = dict(history.history)
    for k, v in metrics_cb.history.items():
        combined_history[k] = v
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_models(model, timestamp)
    plot_metrics(combined_history, timestamp)
    plot_predictions(model, X_test, y_test_norm, test_df, Y_MIN, Y_MAX)
    return model

def save_models(model, timestamp):
    keras_path = f'../../webapp/models/glucose_model_{timestamp}.h5'
    model.save(keras_path, save_format='h5')
    print(f"Saved Keras model to {keras_path}")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path = f'../../webapp/models/glucose_model_{timestamp}.tflite'
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    print(f"Saved TFLite model to {tflite_path}")
    interpreter = tf.lite.Interpreter(model_content=tflite_model)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    print("Expected input shape:", input_details[0]['shape'])

if __name__ == "__main__":
    try:
        train_model()
        print("Training completed successfully!")
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during training: {str(e)}")
        raise
