import streamlit as st
from PIL import Image, ImageDraw, ImageStat
import numpy as np

# Tittel på appen
st.title("Drone Fotoinnstillingsanbefaling (Uten Google API)")

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

    # Funksjon for å analysere lysstyrken i bildet
    def analyze_brightness(image):
        # Konverter bildet til gråtoner og beregn gjennomsnittlig lysstyrke
        grayscale_image = image.convert("L")
        stat = ImageStat.Stat(grayscale_image)
        brightness = stat.mean[0] / 255  # Normaliser lysstyrken til verdi mellom 0 og 1
        return brightness

    # Funksjon for å analysere dominerende farger
    def analyze_colors(image):
        image = image.resize((100, 100))  # Reduser størrelsen for raskere beregning
        colors = np.array(image).reshape(-1, 3)
        avg_color = colors.mean(axis=0)  # Gjennomsnittlig farge (RGB)
        return avg_color

    # Beregn lysstyrke og farger
    brightness = analyze_brightness(image)
    avg_color = analyze_colors(image)

    # Generer anbefalinger basert på lysstyrke og farge
    def generate_recommendations(brightness, avg_color, fixed_aperture=None):
        iso = 100
        shutter_speed = "1/250s"
        aperture = fixed_aperture if fixed_aperture else "f/5.6"
        white_balance = "Auto"

        # Juster ISO og lukkerhastighet basert på lysstyrke
        if brightness < 0.3:
            iso = 800
            shutter_speed = "1/125s"
        elif brightness < 0.6:
            iso = 400
            shutter_speed = "1/200s"
        else:
            iso = 100
            shutter_speed = "1/500s"

        # Juster hvitbalanse basert på dominerende farge
        r, g, b = avg_color
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
    def highlight_image_areas(image, brightness, avg_color):
        image_with_boxes = image.copy()
        draw = ImageDraw.Draw(image_with_boxes)
        width, height = image.size
        
        # Marker områder basert på lysstyrke og farger
        recommendations_text = ""
        if brightness > 0.8:
            color = "red"
            recommendations_text += "Områder er overeksponert - vurder lavere ISO.\n"
            draw.rectangle([(width*0.1, height*0.1), (width*0.9, height*0.9)], outline=color, width=3)
        elif brightness < 0.2:
            color = "blue"
            recommendations_text += "Områder er undereksponert - vurder høyere ISO.\n"
            draw.rectangle([(width*0.1, height*0.1), (width*0.9, height*0.9)], outline=color, width=3)

        st.image(image_with_boxes, caption="Bilde med markerte områder", use_column_width=True)
        if recommendations_text:
            st.write("Anbefalinger for justeringer:")
            st.write(recommendations_text)
        else:
            st.write("Bildet ser ut til å ha balanserte lysforhold.")

    # Generer og vis anbefalinger
    st.write("Analyseresultater og anbefalte innstillinger:")
    generate_recommendations(brightness, avg_color, aperture_value)
    
    # Marker og vis bilde med anbefalte justeringer
    st.write("Bilde med markerte områder som trenger oppmerksomhet:")
    highlight_image_areas(image, brightness, avg_color)

