import streamlit as st
from PIL import Image, ImageDraw, ImageStat, ExifTags
import numpy as np

# Tittel på appen
st.title("Avansert Drone Fotoinnstillingsanbefaling med Nøyaktig Eksponeringsanalyse og ND-filter")

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
        st.session_state['uploaded'] = True
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
                        brightness = stat.mean[0] / 255  # Normaliser lysstyrken til verdi mellom 0 og 1
                        brightness_map.append(brightness)
                all_brightness_values.append(np.mean(brightness_map))

            # Ta gjennomsnitt, standardavvik og median av flere analyserunder
            return np.mean(all_brightness_values), np.std(all_brightness_values), np.median(all_brightness_values)

        # Funksjon for å analysere gjennomsnittsfarge
        def analyze_colors(image):
            image = image.resize((100, 100))
            colors = np.array(image).reshape(-1, 3)
            avg_color = colors.mean(axis=0)
            return avg_color

        # Beregn lysstyrke og farger
        avg_brightness, brightness_std, median_brightness = analyze_brightness_regions(image)
        avg_color = analyze_colors(image)

        # Generer anbefalinger med og uten ND-filter basert på lysstyrke og farge
        def generate_recommendations(avg_brightness, brightness_std, median_brightness, avg_color, fixed_aperture=None):
            iso_no_filter = 100
            iso_with_filter = 100
            shutter_speed_no_filter = "1/250s"
            shutter_speed_with_filter = "1/250s"
            aperture = fixed_aperture if fixed_aperture else "f/5.6"
            white_balance = "Auto"
            nd_filter = "Ingen"

            # Juster ISO og lukkerhastighet basert på gjennomsnittlig og median lysstyrke, samt standardavvik
            if avg_brightness < 0.3 or median_brightness < 0.3:
                iso_no_filter = 800
                shutter_speed_no_filter = "1/125s"
            elif avg_brightness < 0.6:
                iso_no_filter = 400
                shutter_speed_no_filter = "1/200s"
            else:
                iso_no_filter = 100
                shutter_speed_no_filter = "1/500s"

            # Anbefalinger med ND-filter justert basert på lysstyrkenivå
            if avg_brightness > 0.8 or brightness_std > 0.2:
                iso_with_filter = 1600
                shutter_speed_with_filter = "1/60s"
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
                iso_with_filter = 800
                shutter_speed_with_filter = "1/125s"
                nd_filter = "ND4"
            else:
                iso_with_filter = 400
                shutter_speed_with_filter = "1/200s"
                nd_filter = "ND4"

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

        # Funksjon for å markere over- og undereksponerte områder
        def highlight_image_areas(image, avg_brightness, brightness_std, median_brightness):
            image_with_boxes = image.convert("RGBA")
            overlay = Image.new("RGBA", image_with_boxes.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            width, height = image.size
            region_width = width // 20
            region_height = height // 20

            overexposed = avg_brightness > 0.8 or brightness_std > 0.2
            underexposed = avg_brightness < 0.3 or median_brightness < 0.3

            # Hvis bildet er overeksponert, fyll med grønn skravering
            if overexposed:
                draw.rectangle([(0, 0), (width, height)], outline="green", width=3, fill=(0, 255, 0, 80))
            # Hvis bildet er undereksponert, fyll med rød skravering
            if underexposed:
                draw.rectangle([(0, 0), (width, height)], outline="red", width=3, fill=(255, 0, 0, 80))

            image_with_boxes = Image.alpha_composite(image_with_boxes, overlay)
            st.image(image_with_boxes, caption="Bilde med markerte eksponeringsområder", use_column_width=True)
            
            if overexposed and underexposed:
                st.write("Generell anbefaling: Bildet inneholder både overeksponerte og undereksponerte områder. Juster ISO, bruk ND-filter og kontroller lysforholdene.")
            elif overexposed:
                st.write("Generell anbefaling: Bildet har overeksponerte områder. Vurder å bruke et ND-filter og redusere ISO.")
            elif underexposed:
                st.write("Generell anbefaling: Bildet har undereksponerte områder. Øk ISO for å få bedre eksponering.")
            else:
                st.write("Bildet ser ut til å ha balanserte lysforhold.")

        # Generer og vis anbefalinger
        st.write("Analyseresultater og anbefalte innstillinger:")
        generate_recommendations(avg_brightness, brightness_std, median_brightness, avg_color, aperture_value)
        
        # Marker og vis bilde med anbefalte justeringer
        st.write("Bilde med markerte eksponeringsområder:")
        highlight_image_areas(image, avg_brightness, brightness_std, median_brightness)

# Knapp for å laste opp et nytt bilde
if st.session_state['uploaded']:
    if st.button("Last opp et nytt bilde"):
        st.session_state['uploaded'] = False
        st.write("Du kan nå laste opp et nytt bilde ved å bruke opplastingsboksen ovenfor.")

