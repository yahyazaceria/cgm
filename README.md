# OASIS – AI-Enhanced Non-Invasive Glucose Monitoring System (CGM)
![hippo](https://github.com/yahyazaceria/cgm/blob/74a41d8ec794e3894c19bc23daef972b7a5afeed/circuit.png)
---
## Project Description
OASIS (Optical Spectroscopy Integrated System) is a non-invasive, affordable glucose monitoring solution using optical spectroscopy techniques and advanced machine learning. The system employs spectroscopy imaging combined with convolutional neural networks (CNNs), transfer learning, and generative adversarial networks (GANs) for reliable and accurate glucose prediction.

---
## Key Components
- **Optical Spectroscopy Hardware**
  - Raspberry Pi-based prototype.
  - Near-infrared (NIR) and mid-infrared (Mid-IR) sensors.
  - Visible red laser diode and photodiode camera.

- **Data Acquisition and Processing**
  - Scripts to capture hyperspectral images.
  - Data normalization, filtering, and spectral feature extraction.

- **AI Models and Training**
  - CNN architecture for glucose level prediction.
  - Transfer learning integration for enhanced performance.
  - GAN-based data augmentation to increase dataset size and variability.

- **Validation and Calibration**
  - Reference glucose measurements using commercial glucometers.
  - Calibration procedures accounting for skin hydration and melanin variations.
  - Statistical analysis for system validation.

