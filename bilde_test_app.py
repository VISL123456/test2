import streamlit as st
from PIL import Image, ImageDraw, ImageStat, ExifTags
import numpy as np
import json
import os

# Fil for lagring av brukerdata
feedback_file = "user_feedback.json"

# Henter tilbakemeldinger fra fil
def load_feedback():
    if os.path.exists(feedback_file):
        with open(feedback_file, "r") as f:
            return json.load(f)
    return {"iso": [], "shutter_speed": [], "nd_filter": []}

# Lagrer tilbakemeldinger til fil
def save_feedback(feedback):
    data = load_feedback()
    for key in feedback:
        data[key].append(feedback[key])
    with open(feedback_file, "w") as f:
        json.dump(data, f)

# Brukerdata for læring
user_feedback = load_feedback()

# Genererer gjennomsnittlig anbefaling basert på tidligere tilbakemeldinger
def average_user_feedback():
    if user_feedback["iso"]:
        avg_iso = int(np.mean(user_feedback["iso"]))
    else:
        avg_iso = 400  # Standardverdi hvis ingen data
    return avg_iso

# Tittel på appen
st.title("Selvforbedrende Drone Fotoinnstillingsanbefaling med Brukerlæring")

# Opplastingsstatus
if 'uploaded' not in st.session_state:
    st.session_state['uploaded'] = False
if 'feedback_submitted' not in st.session_state:
    st.session_state['feedback_submitted'] = False

# Hvis brukeren allerede har lastet opp et bilde
if not st.session_state['uploaded']:
    # Velg om dronen har fast blenderåpning
    fast_aperture = st.selectbox("Har dronen fast blenderåpning?", ["Ja", "Nei"])
    aperture_value = None
    if fast_aperture == "Ja":
        aperture_value = st.text_input("Angi blenderåpning (f-verdi, f.eks. f/2.8)")

    # Last opp bildet
    uploaded_file = st.file_uploader("Last opp et bilde", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.session_state['uploaded'] = True
        st.session_state['feedback_submitted'] = False
        image = Image.open(uploaded_file)

        # Bevarer bildeorienteringen
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        try:
            exif = dict(image._getexif().items())
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass

        st.image(image, caption='Opplastet bilde', use_column_width=True)
        
        # Funksjon for å beregne gjennomsnittlig lysstyrke over flere analyserunder
        def analyze_brightness_regions(image, grid_size=(20, 20), rounds=5):
            grayscale_image = image.convert("L")
            width, height = grayscale_image.size
            region_width = width // grid_size[0]
            region_height = height // grid_size[1]
            all_brightness_values = []

            for _ in range(rounds):
                brightness_map = []
                for i in range(grid_size[0]):
                    for j in range(grid_size[1]):
                        left = i * region_width
                        upper = j * region_height
                        right = (i + 1) * region_width
                        lower = (j + 1) * region_height
                        region = grayscale_image.crop((left, upper, right, lower))
                        stat = ImageStat.Stat(region)
                        brightness = stat.mean[0] / 255
                        brightness_map.append(brightness)
                all_brightness_values.append(np.mean(brightness_map))

            return np.mean(all_brightness_values), np.std(all_brightness_values), np.median(all_brightness_values), brightness_map

        # Funksjon for å analysere gjennomsnittsfarge
        def analyze_colors(image):
            image = image.resize((100, 100))
            colors = np.array(image).reshape(-1, 3)
            avg_color = colors.mean(axis=0)
            return avg_color

        # Beregn lysstyrke og farger
        avg_brightness, brightness_std, median_brightness, brightness_map = analyze_brightness_regions(image)
        avg_color = analyze_colors(image)

        # Generer anbefalinger med og uten ND-filter basert på lysstyrke og farge
        def generate_recommendations(avg_brightness, brightness_std, median_brightness, avg_color, fixed_aperture=None):
            # Bruker tidligere tilbakemelding for ISO
            iso_no_filter = average_user_feedback()
            iso_with_filter = iso_no_filter * 2  # Økt ISO med ND-filter
            shutter_speed_no_filter = "1/250s"
            shutter_speed_with_filter = "1/125s"
            aperture = fixed_aperture if fixed_aperture else "f/5.6"
            white_balance = "Auto"
            nd_filter = "Ingen"

            if avg_brightness > 0.8 or brightness_std > 0.2:
                if avg_brightness > 0.9 or brightness_std > 0.25:
                    nd_filter = "ND64"
                elif avg_brightness > 0.8:
                    nd_filter = "ND32"
                elif avg_brightness > 0.7:
                    nd_filter = "ND16"
                elif avg_brightness > 0.6:
                    nd_filter = "ND8"
                else:
                    nd_filter = "ND4"
            elif avg_brightness < 0.6:
                nd_filter = "ND4"

            r, g, b = avg_color
            if r > 200 and g > 200 and b > 200:
                white_balance = "Dagslys"
            elif b > r and b > g:
                white_balance = "Skumring"
            elif r > g and r > b:
                white_balance = "Solnedgang"

            recommendations = f"""Anbefalte Innstillinger:
            Uten ND-filter:
            - ISO: {iso_no_filter}
            - Lukkerhastighet: {shutter_speed_no_filter}
            - Blenderåpning: {aperture}
            - Hvitbalanse: {white_balance}

            Med ND-filter ({nd_filter}):
            - ISO: {iso_with_filter}
            - Lukkerhastighet: {shutter_speed_with_filter}
            - Blenderåpning: {aperture}
            - Hvitbalanse: {white_balance}
            """
            
            st.write(recommendations)
            return iso_no_filter, shutter_speed_no_filter, nd_filter

        # Funksjon for å markere over- og undereksponerte områder
        def highlight_image_areas(image, brightness_map, grid_size=(20, 20)):
            image_with_boxes = image.convert("RGBA")
            overlay = Image.new("RGBA", image_with_boxes.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            width, height = image.size
            region_width = width // grid_size[0]
            region_height = height // grid_size[1]

            for i, brightness in enumerate(brightness_map):
                x = (i % grid_size[0]) * region_width
                y = (i // grid_size[0]) * region_height
                if brightness > 0.8:
                    draw.rectangle([(x, y), (x + region_width, y + region_height)], outline="green", width=3, fill=(0, 255, 0, 80))
                elif brightness < 0.2:
                    draw.rectangle([(x, y), (x + region_width, y + region_height)], outline="red", width=3, fill=(255, 0, 0, 80))

            image_with_boxes = Image.alpha_composite(image_with_boxes, overlay)
            st.image(image_with_boxes, caption="Bilde med markerte eksponeringsområder", use_column_width=True)

        # Generer og vis anbefalinger
        st.write("Analyseresultater og anbefalte innstillinger:")
        iso, shutter_speed, nd_filter = generate_recommendations(avg_brightness, brightness_std, median_brightness, avg_color, aperture_value)

        # Marker og vis bilde med eksponeringsanalyse
        st.write("Bilde med markerte eksponeringsområder:")
        highlight_image_areas(image, brightness_map)

        # Tilbakemelding fra bruker uten app-tilbakestilling
        st.write("Var anbefalingene nyttige? Del dine egne innstillinger!")
        feedback_iso = st.number_input("Hvilken ISO brukte du?", min_value=100, max_value=6400, step=100, key="feedback_iso")
        feedback_shutter_speed = st.selectbox("Hvilken lukkerhastighet brukte du?", ["1/1000s", "1/500s", "1/250s", "1/125s", "1/60s"], key="feedback_shutter_speed")
        feedback_nd_filter = st.selectbox("Hvilket ND-filter brukte du?", ["Ingen", "ND4", "ND8", "ND16", "ND32", "ND64"], key="feedback_nd_filter")

        if st.button("Send tilbakemelding") and not st.session_state['feedback_submitted']:
            save_feedback({"iso": feedback_iso, "shutter_speed": feedback_shutter_speed, "nd_filter": feedback_nd_filter})
            st.session_state['feedback_submitted'] = True
            st.write("Takk for din tilbakemelding! Dette vil hjelpe oss med å forbedre anbefalingene.")


