import streamlit as st
import cv2
import numpy as np
from PIL import Image

# Monkeypatch to fix AttributeError with newer Streamlit versions
import streamlit.elements.image
from streamlit.elements.lib import image_utils

# Save the original function
original_image_to_url = image_utils.image_to_url

# Define a mock class for LayoutConfig
class MockLayoutConfig:
    def __init__(self, width):
        self.width = width

# Define the wrapper
def image_to_url_wrapper(image, width, clamp, channels, output_format, image_id):
    # Check if width is an int (which st_canvas passes)
    if isinstance(width, int):
        # Wrap it in the config object expected by new Streamlit
        config = MockLayoutConfig(width)
        return original_image_to_url(image, config, clamp, channels, output_format, image_id)
    else:
        # If it's not an int, just pass it through (maybe it's already correct)
        return original_image_to_url(image, width, clamp, channels, output_format, image_id)

# Apply the monkeypatch
streamlit.elements.image.image_to_url = image_to_url_wrapper

from streamlit_drawable_canvas import st_canvas

# --- Configuración de la página ---
st.set_page_config(page_title="Generador de Código OpenCV", layout="wide")
st.title("🎨 Generador de Coordenadas para OpenCV")
st.markdown("""
Dibuja sobre la imagen y obtén el código `cv2.line`, `cv2.circle` o `cv2.rectangle` exacto.
Ideal para definir Regiones de Interés (ROI).
""")

# --- Funciones Auxiliares ---
def hex_to_bgr(hex_color):
    """Convierte color Hex de Streamlit a formato BGR de OpenCV."""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # OpenCV usa BGR, no RGB, así que invertimos el orden
    return (rgb[2], rgb[1], rgb[0])

# --- Barra Lateral (Controles) ---
with st.sidebar:
    st.header("Configuración")
    
    # 1. Cargar Imagen
    uploaded_file = st.file_uploader("1. Carga tu imagen de fondo:", type=["png", "jpg", "jpeg"])
    
    background_image = None
    canvas_width = 700
    canvas_height = 500

    if uploaded_file is not None:
        image_pil = Image.open(uploaded_file)
        # Convertimos a array numpy para poder leer dimensiones si fuera necesario después
        img_np = np.array(image_pil)
        # Ajustamos el tamaño del canvas al de la imagen (limitando el ancho para que quepa)
        canvas_width = img_np.shape[1]
        canvas_height = img_np.shape[0]
        background_image = image_pil
        st.success(f"Imagen cargada: {canvas_width}x{canvas_height}")
    else:
        st.info("Usando lienzo negro por defecto.")

    st.divider()

    # 2. Herramientas de Dibujo
    st.subheader("2. Herramientas")
    drawing_mode = st.radio(
        "Tipo de figura:",
        ("rect", "circle", "line"),
        format_func=lambda x: {"rect": "Rectángulo", "circle": "Círculo", "line": "Línea"}.get(x)
    )

    # 3. Estilo
    st.subheader("3. Estilo (para el código generado)")
    # Picker de color de Streamlit devuelve Hex
    stroke_color_hex = st.color_picker("Color del trazo:", "#00FF00")
    # Convertimos a BGR para el código de OpenCV final
    stroke_color_bgr = hex_to_bgr(stroke_color_hex)
    
    stroke_width = st.slider("Grosor de la línea:", 1, 10, 2)

# --- Área Principal (Lienzo) ---

# Creamos dos columnas: izquierda para el lienzo, derecha para el código
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Lienzo de Dibujo")
    # Este es el componente mágico que permite dibujar en la web
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.0)",  # Relleno transparente
        stroke_width=stroke_width,
        stroke_color=stroke_color_hex,
        background_image=background_image if background_image else None,
        background_color="#000000" if background_image is None else "#FFFFFF",
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        key="canvas",
        display_toolbar=True, # Muestra botones para deshacer/borrar en el canvas
    )

# --- Procesamiento de Resultados ---
with col2:
    st.subheader("Código OpenCV Generado")
    st.write("Copia estos snippets directamente en tu script de Python.")

    if canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        
        if not objects:
            st.info("Dibuja algo en el lienzo para ver el código aquí.")
        
        code_snippets = []

        for obj in objects:
            # El canvas devuelve coordenadas de JavaScript (left, top, width, height)
            # Necesitamos convertirlas a la sintaxis de OpenCV.
            
            if obj["type"] == "rect":
                x1 = int(obj["left"])
                y1 = int(obj["top"])
                x2 = int(obj["left"] + obj["width"])
                y2 = int(obj["top"] + obj["height"])
                snippet = f"cv2.rectangle(img, ({x1}, {y1}), ({x2}, {y2}), {stroke_color_bgr}, {stroke_width})"
                code_snippets.append(snippet)
                
            elif obj["type"] == "line":
                x1 = int(obj["x1"])
                y1 = int(obj["y1"])
                x2 = int(obj["x2"])
                y2 = int(obj["y2"])
                snippet = f"cv2.line(img, ({x1}, {y1}), ({x2}, {y2}), {stroke_color_bgr}, {stroke_width})"
                code_snippets.append(snippet)

            elif obj["type"] == "circle":
                # El canvas dibuja círculos basados en un cuadro delimitador (bounding box)
                center_x = int(obj["left"] + obj["width"] / 2)
                center_y = int(obj["top"] + obj["height"] / 2)
                # Asumimos un círculo perfecto, tomamos el radio del ancho
                radius = int(obj["width"] / 2)
                
                snippet = f"cv2.circle(img, ({center_x}, {center_y}), {radius}, {stroke_color_bgr}, {stroke_width})"
                code_snippets.append(snippet)

        # Mostrar el código resultante en bloques bonitos
        for snippet in code_snippets:
            st.code(snippet, language="python")

    else:
        st.warning("Esperando interacción con el lienzo...")

# --- Nota al pie ---
st.divider()
st.caption("Nota: Los colores se convierten automáticamente de Hex (Streamlit) a BGR (tuplas de OpenCV).")