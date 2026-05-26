# AI_Project
Repo for AI Programming with Python


# Possible projects
## Physics inspired neural network - lagrangian neural network (old project by david, might require too much knowledge of Physics)
- Network trying to predict the movement/time evolved states of physical systems(pendulum, double pendulum, weight and feathrer, charged particle in electrical field)
- already available for this project:
  - Written and trained networks for different systems and analysis of them in form of google collab sheets
     - https://colab.research.google.com/drive/1HcmLWDwO4N9a9TM26wW2MqhZ6e0-yrNO?usp=sharing
     - https://colab.research.google.com/drive/18t5leTnVJNHsjBG31g_1gdYMLLVKASAG?usp=sharing
     - https://colab.research.google.com/drive/1ROr7G9g3nVtCQ-OSYJq82bSSPORJn4gp?usp=sharing
  - powerpoint for full project(very physics heavy)
     - https://docs.google.com/presentation/d/12_cVzqgiNnJ_K5UTyBxjegluyPMubgTwmQ79LjFMRPw/edit?usp=sharing
  - mid project report(also somewhat physics heavy)
     - see file
  - paper and tutorial of original paper detailing workings of the network
     - https://colab.research.google.com/drive/1peVkVS99uwYsBJ0G-NkZ5uo9OSYwNXg2?usp=sharing 
 
## IMDB sentiment analysis(old project by jonas)


## Draw Equation Solver

Draw handwritten math expressions and get instant results using a CNN-based digit recognizer + computer vision.

= Features

- Draw digits and operators directly on canvas

- CNN model trained on MNIST (~99% accuracy)

- Supports + − × ÷

- Smart operator detection (geometry-based)

- Real-time prediction with Streamlit UI

= How it works

#enum(

  "Draw input on canvas",

  "Image preprocessing (threshold + dilation)",

  "Contour detection and symbol segmentation",

  "Operator classification (geometry rules)",

  "Digit classification (CNN model)",

  "Safe evaluation using AST"

)

= Installation

```bash

git clone <your-repo-url>

cd draw-equation-solver

python -m venv venv

source venv/bin/activate

venv\Scripts\activate

pip install -r requirements.txt