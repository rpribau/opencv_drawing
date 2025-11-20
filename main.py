import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="OpenCV Builder Cloud", layout="centered")
st.title("☁️ Generador OpenCV: Versión Cloud")
st.markdown("""
**Instrucciones:**
1. Sube tu imagen.
2. Selecciona la herramienta **Punto** o **Rectángulo**.
3. Dibuja y obtén el código abajo.
""")

# --- FUNCIONES ---
def hex_to_bgr(hex_color):
    hex = hex_color.lstrip('#')
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))[::-1]

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Resolución del Lienzo")
    
    # Inputs para cambiar la resolución (Por defecto 320x240)
    canvas_width = st.number_input("Ancho (px):", min_value=100, max_value=3000, value=320, step=10)
    canvas_height = st.number_input("Alto (px):", min_value=100, max_value=3000, value=240, step=10)

    st.divider()
    st.header("2. Imagen y Herramientas")
    
    uploaded_file = st.file_uploader("Cargar Imagen", type=["png", "jpg", "jpeg"])
    
    # --- CORRECCIÓN AQUÍ: FORZAR RGB ---
    if uploaded_file:
        try:
            img_pil = Image.open(uploaded_file)
            # .convert("RGB") elimina canales alfa (transparencias) que rompen el canvas en web
            img_pil = img_pil.convert("RGB") 
            bg_image = img_pil.resize((canvas_width, canvas_height))
            file_id = uploaded_file.name
        except Exception as e:
            st.error(f"Error al procesar imagen: {e}")
            bg_image = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
            file_id = "error"
    else:
        # Lienzo negro por defecto
        bg_image = Image.new("RGB", (canvas_width, canvas_height), (0,0,0))
        file_id = "new"

    mode = st.radio("Herramienta:", 
             ("point", "rect", "circle"),
             format_func=lambda x: {
                 "point": "📍 Puntos (Click A -> Click B)", 
                 "rect": "⬜ Rectángulo", 
                 "circle": "⭕ Círculo"
             }.get(x))
    
    color = st.color_picker("Color", "#00FF00")
    stroke = st.slider("Grosor", 1, 5, 2)
    
    if st.button("🗑️ Borrar todo"):
        st.session_state["reset_counter"] = st.session_state.get("reset_counter", 0) + 1

# --- LÓGICA PRINCIPAL ---

st.subheader(f"1. Lienzo de Dibujo ({canvas_width}x{canvas_height})")

# Key dinámica para reiniciar si cambia algo importante
key = f"cv_v10_{file_id}_{canvas_width}_{canvas_height}_{st.session_state.get('reset_counter', 0)}"

with st.container(border=True):
    c_left, c_center, c_right = st.columns([1, 3, 1])
    with c_center:
        canvas = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=stroke if mode != "point" else 5,
            stroke_color=color,
            background_image=bg_image,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode=mode,
            point_display_radius=3,
            key=key,
            display_toolbar=True 
        )

st.divider()
st.subheader("2. Código Generado")

if canvas.json_data and canvas.json_data["objects"]:
    objects = canvas.json_data["objects"]
    color_bgr = hex_to_bgr(color)
    
    if mode == "point":
        points = [obj for obj in objects if obj["type"] == "circle"]
        if len(points) >= 2:
            st.success(f"✅ {len(points)} puntos. Generando líneas...")
            code_block = ""
            for i in range(0, len(points) - 1, 2):
                p1 = points[i]
                p2 = points[i+1]
                x1 = int(p1["left"] + p1["radius"]) 
                y1 = int(p1["top"] + p1["radius"])
                x2 = int(p2["left"] + p2["radius"])
                y2 = int(p2["top"] + p2["radius"])
                code_block += f"cv2.line(img, ({x1}, {y1}), ({x2}, {y2}), {color_bgr}, {stroke})\n"
            st.code(code_block, language="python")
        elif len(points) == 1:
            st.info("📍 Punto 1 marcado. Haz click en el destino.")
        else:
            st.info("Haz click para marcar puntos.")

    else:
        code_block = ""
        for obj in objects:
            if obj["type"] == "rect":
                x1, y1 = int(obj["left"]), int(obj["top"])
                x2, y2 = int(x1 + obj["width"]), int(y1 + obj["height"])
                code_block += f"cv2.rectangle(img, ({x1}, {y1}), ({x2}, {y2}), {color_bgr}, {stroke})\n"
            elif obj["type"] == "circle" and mode == "circle":
                cx = int(obj["left"] + obj["radius"])
                cy = int(obj["top"] + obj["radius"])
                r = int(obj["radius"])
                code_block += f"cv2.circle(img, ({cx}, {cy}), {r}, {color_bgr}, {stroke})\n"
        st.code(code_block, language="python")
else:
    st.info("Dibuja para ver el código.")