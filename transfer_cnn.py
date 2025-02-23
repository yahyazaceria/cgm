import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import numpy as np
import os
from sklearn.model_selection import train_test_split
import pandas as pd
import matplotlib.pyplot as plt

class GlucoseCNN:
    def __init__(self, image_size=(224, 224)):
        self.image_size = image_size
        self.model = self._build_model()

    def _build_model(self):
        # Load pre-trained ResNet50 with transfer learning
        base_model = tf.keras.applications.ResNet50(
            weights='imagenet',
            include_top=False,
            input_shape=(*self.image_size, 3)
        )
        
        # First: train only the top layers
        for layer in base_model.layers:
            layer.trainable = False
        
        # Add custom top layers
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = Dense(512, activation='relu')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = Dropout(0.3)(x)
        x = Dense(256, activation='relu')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = Dropout(0.2)(x)
        predictions = Dense(1, activation='linear')(x)
        
        model = Model(inputs=base_model.input, outputs=predictions)
        return model

    def prepare_data(self, data_dir):
        csv_path = os.path.join(data_dir, 'photos_data.csv')
        glucose_data = pd.read_csv(csv_path)
        
        # Normalize glucose levels
        mean_glucose = glucose_data['Glucose Level'].mean()
        std_glucose = glucose_data['Glucose Level'].std()
        glucose_data['Glucose Level'] = (glucose_data['Glucose Level'] - mean_glucose) / std_glucose
        
        images = []
        glucose_levels = []
        
        for _, row in glucose_data.iterrows():
            img_path = os.path.join(data_dir, 'images', row['Filename'])
            try:
                img = tf.keras.preprocessing.image.load_img(
                    img_path, target_size=self.image_size
                )
                img_array = tf.keras.preprocessing.image.img_to_array(img)
                # Normalize images
                img_array = tf.keras.applications.resnet50.preprocess_input(img_array)
                
                images.append(img_array)
                glucose_levels.append(float(row['Glucose Level']))
                
            except Exception as e:
                print(f"Error processing image {row['Filename']}: {str(e)}")
                continue

        X = np.array(images)
        y = np.array(glucose_levels)
        
        # Store normalization parameters
        self.glucose_mean = mean_glucose
        self.glucose_std = std_glucose
        
        return train_test_split(X, y, test_size=0.2, shuffle=False)

    def train(self, X_train, y_train, X_val, y_val, epochs=50, batch_size=32):
        # Compile model
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        # Train the model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    patience=10,
                    restore_best_weights=True
                )
            ]
        )
        
        # Create a figure with 3 subplots
        plt.figure(figsize=(15, 5))
        
        # Plot loss
        plt.subplot(1, 3, 1)
        plt.plot(history.history['loss'], label='Training Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss (MSE)')
        plt.legend()
        
        # Plot MAE
        plt.subplot(1, 3, 2)
        plt.plot(history.history['mae'], label='Training MAE')
        plt.plot(history.history['val_mae'], label='Validation MAE')
        plt.title('Mean Absolute Error')
        plt.xlabel('Epoch')
        plt.ylabel('MAE (mg/dL)')
        plt.legend()
        
        # Plot MAPE (accuracy)
        plt.subplot(1, 3, 3)
        plt.plot(history.history['mape'], label='Training MAPE')
        plt.plot(history.history['val_mape'], label='Validation MAPE')
        plt.title('Mean Absolute Percentage Error')
        plt.xlabel('Epoch')
        plt.ylabel('MAPE (%)')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('training_metrics.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return history

    def predict(self, X):
        # Get normalized predictions
        pred_norm = self.model.predict(X)
        # Denormalize
        return pred_norm * self.glucose_std + self.glucose_mean

    def save_model(self, path):
        self.model.save(path)

def main():
    # Initialize model
    cnn = GlucoseCNN()
    
    data_dir = './data'
    
    # Prepare data
    X_train, X_val, y_train, y_val = cnn.prepare_data(data_dir)
    
    # Train model
    history = cnn.train(X_train, y_train, X_val, y_val)
    
    # Save model
    cnn.save_model('glucose_model.h5')
    
    # Print detailed metrics
    final_val_loss = history.history['val_loss'][-1]
    final_val_mae = history.history['val_mae'][-1]
    final_val_mape = history.history['val_mape'][-1]
    
    print("\nFinal Validation Metrics:")
    print(f"Loss (MSE): {final_val_loss:.2f}")
    print(f"Mean Absolute Error: {final_val_mae:.2f} mg/dL")
    print(f"Mean Absolute Percentage Error: {final_val_mape:.2f}%")
    
    # Make predictions and denormalize both predictions and actual values
    val_pred = cnn.predict(X_val)  # This will denormalize predictions
    y_val_denorm = y_val * cnn.glucose_std + cnn.glucose_mean  # Denormalize actual values
    
    # Calculate metrics using denormalized values
    percent_errors = abs(val_pred - y_val_denorm) / y_val_denorm * 100
    
    print("\nClinical Accuracy Metrics:")
    print(f"Predictions within ±15%: {np.mean(percent_errors <= 15)*100:.1f}%")
    print(f"Predictions within ±10%: {np.mean(percent_errors <= 10)*100:.1f}%")
    print(f"Predictions within ±5%: {np.mean(percent_errors <= 5)*100:.1f}%")
    
    print("\nValue Ranges:")
    print(f"Actual values range: {float(min(y_val_denorm)):.1f} to {float(max(y_val_denorm)):.1f} mg/dL")
    print(f"Predicted values range: {float(min(val_pred)):.1f} to {float(max(val_pred)):.1f} mg/dL")

if __name__ == "__main__":
    main()