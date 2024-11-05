# -*- coding: utf-8 -*-
"""bilde test app

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1hYHQkRPKMfVW080BSYjvwBfGbPQZqWRe
"""



import streamlit as st
import requests
import json
import base64
import cv2
import numpy as np
from PIL import Image

# Sett inn din Google Cloud Vision API-nøkkel her
API_KEY = 'AIzaSyBUQdMP9n95P02q1_Kvc8oHWpf3YgyhQqg'

# Tittel på appen
st.title("Drone Fotoinnstillingsanbefaling")

# Velg om dronen har fast blenderåpning
fast_aperture = st.selectbox("Har dronen fast blenderåpning?", ["Ja", "Nei"])
aperture_value = None
if fast_aperture == "Ja":
    aperture_value = st.text_input("Angi blenderåpning (f-verdi, f.eks. f/2.8)")

# Last opp bildet
uploaded_file = st.file_uploader("Last opp et bilde", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Les bildet og vis det
    image = Image.open(uploaded_file)
    st.image(image, caption='Opplastet bilde', use_column_width=True)

    # Konverter bilde til base64 for API-forespørsel
    image_bytes = uploaded_file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # Send bildet til Google Vision API
    url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "requests": [
            {
                "image": {"content": image_base64},
                "features": [{"type": "LABEL_DETECTION"}, {"type": "IMAGE_PROPERTIES"}]
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    analysis = response.json()

    # Resultater og anbefalinger vises her
    st.write("Analyseresultater og anbefalte innstillinger vises her...")