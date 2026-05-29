# 🧮 Draw Equation Solver

A real-time handwritten mathematical expression recognition system built with TensorFlow, OpenCV, and Streamlit.

Draw mathematical expressions directly on an interactive canvas and receive instant predictions, expression reconstruction, and evaluation results.

------------------------------------------------------------------------------

##  Features

- Interactive drawing canvas powered by Streamlit
- Recognition of handwritten digits (0–9)
- Recognition of arithmetic operators:
  - Addition (+)
  - Subtraction (-)
  - Multiplication (×)
  - Division (÷)
- CNN-based handwritten symbol classification
- Automatic symbol segmentation using OpenCV
- Real-time expression reconstruction
- Safe arithmetic evaluation using Python AST
- Visual debugging with detected bounding boxes and confidence scores
- Lightweight deployment suitable for local execution

------------------------------------------------------------------------------

##  Model Architecture

The recognition engine uses a Convolutional Neural Network (CNN) trained on:

- MNIST handwritten digit dataset
- Handwritten Math Symbols dataset

Supported Classes:

| Class Type | Symbols |
|------------|-----------|
| Digits     | 0–9 |
| Operators  | +, -, ×, ÷ |

Total Classes: 14

------------------------------------------------------------------------------

##  Processing Pipeline

1. User draws an expression on the canvas.
2. Canvas image is converted to grayscale.
3. Image thresholding and dilation are applied.
4. Connected components are detected using contour extraction.
5. Symbols are segmented into individual regions.
6. Each symbol is normalized and centered.
7. CNN predicts the corresponding class.
8. Symbols are reconstructed into a mathematical expression.
9. The expression is safely evaluated.
10. Results are displayed instantly.

------------------------------------------------------------------------------

##  Project Structure

project/
│
├── draw.py
├── model.keras
├── class_names.json
│
├── dataset/
│   ├── add/
│   ├── sub/
│   ├── mul/
│   └── div/
│
├── training_history.json
├── class_info.json
├── evaluation_results.json
├── training_config.json
│
└── README.md

------------------------------------------------------------------------------

##  Requirements

Recommended Python Version:

Python 3.11

Tested Environment:

- Python 3.11
- TensorFlow 2.19.0
- OpenCV 4.x
- Streamlit 1.45+
- NumPy 2.x
- scikit-learn 1.6+
- Albumentations 2.x

------------------------------------------------------------------------------

##  Installation

Clone the repository:

git clone <repository-url>
cd draw-equation-solver

Create a virtual environment.

Linux / macOS:

python -m venv venv
source venv/bin/activate

Windows:

python -m venv venv
venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

------------------------------------------------------------------------------

##  Required Packages

- tensorflow
- opencv-python
- numpy
- streamlit
- streamlit-drawable-canvas
- scikit-learn
- matplotlib
- albumentations

------------------------------------------------------------------------------

## Running the Application

Start the Streamlit application:

streamlit run draw.py

Open the following URL in your browser:

http://localhost:8501

------------------------------------------------------------------------------

## Example

Input:

23+14

Prediction:

23+14

Result:

37

------------------------------------------------------------------------------

##  Technologies Used

- Python
- TensorFlow / Keras
- OpenCV
- NumPy
- Streamlit
- scikit-learn
- Albumentations
- Matplotlib

------------------------------------------------------------------------------

##  Performance

Typical performance achieved during testing:

- Digit Recognition Accuracy: ~99%
- Operator Recognition Accuracy: ~95–99%
- Overall Validation Accuracy: ~98–99%

Performance may vary depending on handwriting style, symbol spacing, and drawing quality.

------------------------------------------------------------------------------