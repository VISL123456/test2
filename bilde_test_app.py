import streamlit as st
import requests
import json
import base64
from PIL import Image, ImageDraw
import numpy as np

# Sett inn din Google Cloud Vision API-nøkkel her
API_KEY = 'AIzaSyBubK99b3Tc6_rWyx_cjdOuTfEVT_RWhv0'

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
    # Send bildet til Google Vision API
response = requests.post(url, headers=headers, data=json.dumps(data))

# Sjekk om det er en feil, og logg hele feilmeldingen fra API-en
if response.status_code != 200:
    st.write("Feil fra Google Vision API:", response.text)  # Logger detaljene i svaret
response.raise_for_status()  # Hev feil hvis statuskode ikke er 200
    response.raise_for_status()
    analysis = response.json()

    # Funksjon for å generere anbefalinger basert på analyse
    def generate_recommendations(analysis, fixed_aperture=None):
        colors = analysis['responses'][0]['imagePropertiesAnnotation']['dominantColors']['colors']
        avg_brightness = sum(color['score'] for color in colors) / len(colors)

        iso = 100
        shutter_speed = "1/250s"
        aperture = fixed_aperture if fixed_aperture else "f/5.6"
        white_balance = "Auto"

        if avg_brightness < 0.3:
            iso = 800
            shutter_speed = "1/125s"
        elif avg_brightness < 0.6:
            iso = 400
            shutter_speed = "1/200s"
        else:
            iso = 100
            shutter_speed = "1/500s"

        for color in colors:
            r, g, b = color['color']['red'], color['color']['green'], color['color']['blue']
            if r > 200 and g > 200 and b > 200:
                white_balance = "Dagslys"
            elif b > r and b > g:
                white_balance = "Skumring"
            elif r > g and r > b:
                white_balance = "Solnedgang"

        recommendations = f"""Anbefalte Innstillinger:
        - ISO: {iso}
        - Lukkerhastighet: {shutter_speed}
        - Blenderåpning: {aperture}
        - Hvitbalanse: {white_balance}
        """
        
        st.write(recommendations)
        return recommendations

    # Funksjon for å markere områder på bildet som trenger oppmerksomhet
    def highlight_image_areas(image, analysis):
        image_with_boxes = image.copy()
        draw = ImageDraw.Draw(image_with_boxes)
        
        colors = analysis['responses'][0]['imagePropertiesAnnotation']['dominantColors']['colors']
        recommendations_text = ""

        for color_info in colors:
            brightness = 0.299 * color_info['color']['red'] + 0.587 * color_info['color']['green'] + 0.114 * color_info['color']['blue']
            width, height = image.size
            x, y = np.random.randint(0, width - 100), np.random.randint(0, height - 50)
            
            if brightness > 200:
                color = "red"
                recommendations_text += "Område markert i rødt er overeksponert - vurder lavere ISO.\n"
            elif brightness < 50:
                color = "blue"
                recommendations_text += "Område markert i blått er undereksponert - vurder høyere ISO.\n"
            else:
                continue

            draw.rectangle([(x, y), (x + 100, y + 50)], outline=color, width=3)
        
        st.image(image_with_boxes, caption="Bilde med markerte områder", use_column_width=True)
        if recommendations_text:
            st.write("Anbefalinger for justeringer:")
            st.write(recommendations_text)
        else:
            st.write("Bildet ser ut til å ha balanserte lysforhold.")

    # Generer og vis anbefalinger
    st.write("Analyseresultater og anbefalte innstillinger:")
    generate_recommendations(analysis, aperture_value)
    
    # Marker og vis bilde med anbefalte justeringer
    st.write("Bilde med markerte områder som trenger oppmerksomhet:")
    highlight_image_areas(image, analysis)
