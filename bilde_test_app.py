import streamlit as st
from PIL import Image, ImageDraw, ImageStat
import numpy as np

# Tittel på appen
st.title("Drone Fotoinnstillingsanbefaling med Forbedret Eksponeringsanalyse og ND-filter")

# Opplastingsstatus
if 'uploaded' not in st.session_state:
    st.session_state['uploaded'] = False

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
        st.session_state['uploaded'] = True  # Oppdater opplastingsstatus
        image = Image.open(uploaded_file)
        st.image(image, caption='Opplastet bilde', use_column_width=True)
        
        # Funksjon for å analysere lysstyrken i bildet over et 20x20 grid
        def analyze_brightness_regions(image, grid_size=(20, 20)):
            grayscale_image = image.convert("L")
            width, height = grayscale_image.size
            region_width = width // grid_size[0]
            region_height = height // grid_size[1]
            brightness_map = []

            for i in range(grid_size[0]):
                for j in range(grid_size[1]):
                    left = i * region_width
                    upper = j * region_height
                    right = (i + 1) * region_width
                    lower = (j + 1) * region_height
                    region = grayscale_image.crop((left, upper, right, lower))
                    stat = ImageStat.Stat(region)
                    brightness = stat.mean[0] / 255  # Normaliser lysstyrken til verdi mellom 0 og 1
                    brightness_map.append((i, j, brightness))
                    
            return brightness_map

        # Funksjon for å analysere gjennomsnittsfarge
        def analyze_colors(image):
            image = image.resize((100, 100))  # Reduser størrelsen for raskere beregning
            colors = np.array(image).reshape(-1, 3)
            avg_color = colors.mean(axis=0)  # Gjennomsnittlig farge (RGB)
            return avg_color

        # Beregn lysstyrke og farger
        brightness_map = analyze_brightness_regions(image)
        avg_color = analyze_colors(image)

        # Generer anbefalinger med og uten ND-filter basert på lysstyrke og farge
        def generate_recommendations(brightness_map, avg_color, fixed_aperture=None):
            iso_no_filter = 100
            iso_with_filter = 100
            shutter_speed_no_filter = "1/250s"
            shutter_speed_with_filter = "1/250s"
            aperture = fixed_aperture if fixed_aperture else "f/5.6"
            white_balance = "Auto"
            nd_filter = "Ingen"

            # Juster ISO og lukkerhastighet basert på gjennomsnittlig lysstyrke i ulike regioner
            overexposed_regions = [b for _, _, b in brightness_map if b > 0.8]
            underexposed_regions = [b for _, _, b in brightness_map if b < 0.2]
            avg_brightness = np.mean([b for _, _, b in brightness_map])

            # Anbefalinger uten ND-filter
            if avg_brightness < 0.3 or underexposed_regions:
                iso_no_filter = 800
                shutter_speed_no_filter = "1/125s"
            elif avg_brightness < 0.6:
                iso_no_filter = 400
                shutter_speed_no_filter = "1/200s"
            else:
                iso_no_filter = 100
                shutter_speed_no_filter = "1/500s"

            # Anbefalinger med ND-filter (for svært lyse forhold)
            if avg_brightness > 0.8 or overexposed_regions:
                iso_with_filter = 1600
                shutter_speed_with_filter = "1/60s"
                nd_filter = "ND8"  # Velg ND8 for svært lyse forhold
            elif avg_brightness > 0.6:
                iso_with_filter = 800
                shutter_speed_with_filter = "1/125s"
                nd_filter = "ND4"  # Velg ND4 for moderat lyse forhold
            else:
                iso_with_filter = 400
                shutter_speed_with_filter = "1/200s"

            # Juster hvitbalanse basert på dominerende farge
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
            return recommendations

        # Funksjon for å markere områder på bildet som trenger oppmerksomhet
        def highlight_image_areas(image, brightness_map):
            image_with_boxes = image.copy()
            draw = ImageDraw.Draw(image_with_boxes)
            width, height = image.size
            region_width = width // 20
            region_height = height // 20

            overexposed_found = False
            underexposed_found = False
            for i, j, brightness in brightness_map:
                left = i * region_width
                upper = j * region_height
                right = (i + 1) * region_width
                lower = (j + 1) * region_height
                if brightness > 0.8:
                    overexposed_found = True
                    draw.rectangle([(left, upper), (right, lower)], outline="red", width=3, fill=(255, 0, 0, 50))
                elif brightness < 0.2:
                    underexposed_found = True
                    draw.rectangle([(left, upper), (right, lower)], outline="red", width=3, fill=(255, 0, 0, 50))

            st.image(image_with_boxes, caption="Bilde med markerte områder", use_column_width=True)
            
            # Generell anbefaling basert på over- eller undereksponering
            if overexposed_found and underexposed_found:
                st.write("Generell anbefaling: Bildet inneholder både overeksponerte og undereksponerte områder. Juster ISO, bruk ND-filter og kontroller lysforholdene.")
            elif overexposed_found:
                st.write("Generell anbefaling: Bildet har overeksponerte områder. Vurder å bruke et ND-filter og redusere ISO.")
            elif underexposed_found:
                st.write("Generell anbefaling: Bildet har undereksponerte områder. Øk ISO for å få bedre eksponering.")
            else:
                st.write("Bildet ser ut til å ha balanserte lysforhold.")

        # Generer og vis anbefalinger
        st.write("Analyseresultater og anbefalte innstillinger:")
        generate_recommendations(brightness_map, avg_color, aperture_value)
        
        # Marker og vis bilde med anbefalte justeringer
        st.write("Bilde med markerte områder som trenger oppmerksomhet:")
        highlight_image_areas(image, brightness_map)

# Knapp for å laste opp et nytt bilde plassert nederst
if st.session_state['uploaded']:
    if st.button("Last opp et nytt bilde"):
        st.session_state['uploaded'] = False  # Nullstiller opplastingsstatus
        st.write("Du kan nå laste opp et nytt bilde ved å bruke opplastingsboksen ovenfor.")
