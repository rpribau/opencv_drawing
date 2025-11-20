import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="OpenCV Builder Flexible", layout="centered")
st.title("🎨 Generador OpenCV: Resolución Flexible")
st.markdown("""
**Modo Puntos (Recomendado):** Haz click en A y luego en B para líneas perfectas.
Puedes cambiar la resolución del lienzo en la barra lateral.
""")

# --- FUNCIONES ---
def hex_to_bgr(hex_color):
    hex = hex_color.lstrip('#')
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))[::-1]

# --- BARRA LATERAL (Configuración) ---
with st.sidebar:
    st.header("1. Resolución del Lienzo")
    st.caption("Define el tamaño de salida para tu código OpenCV.")
    
    # Inputs para cambiar la resolución (Por defecto 320x240)
    canvas_width = st.number_input("Ancho (px):", min_value=100, max_value=3000, value=320, step=10)
    canvas_height = st.number_input("Alto (px):", min_value=100, max_value=3000, value=240, step=10)

    st.divider()
    st.header("2. Imagen y Herramientas")
    
    uploaded_file = st.file_uploader("Cargar Imagen", type=["png", "jpg", "jpeg"])
    
    # Procesamiento de la imagen con la resolución dinámica
    if uploaded_file:
        img_pil = Image.open(uploaded_file)
        # Redimensionamos la imagen cargada a la resolución que eligió el usuario
        bg_image = img_pil.resize((canvas_width, canvas_height))
        file_id = uploaded_file.name
    else:
        # Lienzo negro del tamaño elegido
        bg_image = Image.new("RGB", (canvas_width, canvas_height), (0,0,0))
        file_id = "new"

    # Selector de herramienta
    mode = st.radio("Herramienta:", 
             ("point", "rect", "circle"),
             format_func=lambda x: {
                 "point": "📍 Puntos para Línea (Click A -> Click B)", 
                 "rect": "⬜ Rectángulo", 
                 "circle": "⭕ Círculo"
             }.get(x))
    
    color = st.color_picker("Color", "#00FF00")
    stroke = st.slider("Grosor visual", 1, 5, 2)
    
    if st.button("🗑️ Borrar todo"):
        st.session_state["reset_counter"] = st.session_state.get("reset_counter", 0) + 1

# --- LÓGICA PRINCIPAL ---

# 1. EL LIENZO (Centrado)
st.subheader(f"1. Lienzo de Dibujo ({canvas_width}x{canvas_height})")

# Key dinámica: Incluye width/height para forzar reinicio si cambia la resolución
key = f"cv_v9_{file_id}_{canvas_width}_{canvas_height}_{st.session_state.get('reset_counter', 0)}"

with st.container(border=True):
    # Usamos columnas para centrar visualmente el canvas si es pequeño
    c_left, c_center, c_right = st.columns([1, 3, 1])
    with c_center:
        canvas = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=stroke if mode != "point" else 5,
            stroke_color=color,
            background_image=bg_image,
            update_streamlit=True,
            height=canvas_height, # Usa la variable dinámica
            width=canvas_width,   # Usa la variable dinámica
            drawing_mode=mode,
            point_display_radius=3,
            key=key,
            display_toolbar=True 
        )

st.divider()

# 2. EL CÓDIGO (Abajo)
st.subheader("2. Código Generado")

if canvas.json_data and canvas.json_data["objects"]:
    objects = canvas.json_data["objects"]
    color_bgr = hex_to_bgr(color)
    
    # --- LÓGICA DE PUNTOS (Click-Click) ---
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
            
            if len(points) % 2 != 0:
                st.warning("⚠️ Falta un punto de cierre.")
        elif len(points) == 1:
            st.info("📍 Punto de inicio marcado. Haz click en el destino.")
        else:
            st.info("Haz click para marcar puntos.")

    # --- LÓGICA ESTÁNDAR ---
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
    st.info(f"Dibuja sobre el lienzo de {canvas_width}x{canvas_height} para ver el código.")