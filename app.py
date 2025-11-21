import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from streamlit_drawable_canvas import st_canvas

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="OpenCV Drawing Tool - rpribau", layout="centered")
st.title("OpenCV Drawing Tool")
st.markdown("Dibuja sobre una imagen cargada y genera el código OpenCV correspondiente. Usa las herramientas para crear formas y puntos sobre la imagen sin matarte la cabeza con coordenadas.")

# --- FUNCIONES ---
def hex_to_bgr(hex_color):
    hex = hex_color.lstrip('#')
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))[::-1]

# --- ESTADO DE SESIÓN ---
if "bg_image" not in st.session_state:
    st.session_state["bg_image"] = None
if "file_id" not in st.session_state:
    st.session_state["file_id"] = ""

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    c_width = st.number_input("Ancho:", 100, 3000, 320, 10)
    c_height = st.number_input("Alto:", 100, 3000, 240, 10)
    
    st.divider()
    uploaded_file = st.file_uploader("Cargar Imagen", type=["png", "jpg", "jpeg"])

    # --- PROCESAMIENTO ---
    if uploaded_file is not None:
        current_id = f"{uploaded_file.name}-{c_width}-{c_height}"
        
        # Solo procesamos si cambió el archivo o el tamaño
        if st.session_state["file_id"] != current_id:
            try:
                # Reset del puntero
                uploaded_file.seek(0)
                
                # 1. Cargar y convertir
                img_input = Image.open(uploaded_file).convert("RGB")
                
                # 2. Resize
                img_resized = img_input.resize((c_width, c_height))
                
                # 3. Limpieza profunda (Numpy -> Image) para romper referencias
                clean_array = np.array(img_resized)
                img_final = Image.fromarray(clean_array)
                
                # Guardar en sesión
                st.session_state["bg_image"] = img_final
                st.session_state["file_id"] = current_id
                
            except Exception as e:
                st.error(f"Error: {e}")

    # Preview
    if st.session_state["bg_image"]:
        st.image(st.session_state["bg_image"], caption="Cargada OK", use_column_width=True)

    st.divider()
    mode = st.radio("Herramienta:", ("point", "rect", "circle"),
             format_func=lambda x: {"point": "📍 Puntos", "rect": "⬜ Rectángulo", "circle": "⭕ Círculo"}.get(x))
    color = st.color_picker("Color", "#00FF00")
    stroke = st.slider("Grosor", 1, 5, 2)
    
    if st.button("🗑️ Limpiar"):
        st.session_state["reset_counter"] = st.session_state.get("reset_counter", 0) + 1

# --- LIENZO ---
st.subheader(f"Lienzo ({c_width}x{c_height})")

if st.session_state["bg_image"]:
    final_bg = st.session_state["bg_image"]
else:
    final_bg = Image.new("RGB", (c_width, c_height), (0,0,0))

key = f"hf_{st.session_state['file_id']}_{mode}_{st.session_state.get('reset_counter', 0)}"

with st.container(border=True):
    # Columnas para centrar
    col_c = st.columns([1, 5, 1])[1]
    with col_c:
        canvas = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=stroke if mode != "point" else 5,
            stroke_color=color,
            background_image=final_bg,
            update_streamlit=True,
            height=c_height,
            width=c_width,
            drawing_mode=mode,
            point_display_radius=3,
            key=key,
            display_toolbar=True 
        )

# --- CÓDIGO ---
st.divider()
st.subheader("Código Generado")

if canvas.json_data and canvas.json_data["objects"]:
    objects = canvas.json_data["objects"]
    color_bgr = hex_to_bgr(color)
    
    if mode == "point":
        points = [obj for obj in objects if obj["type"] == "circle"]
        if len(points) >= 2:
            st.success(f"✅ {len(points)} puntos. Uniendo...")
            code = ""
            for i in range(0, len(points) - 1, 2):
                p1, p2 = points[i], points[i+1]
                x1, y1 = int(p1["left"]+p1["radius"]), int(p1["top"]+p1["radius"])
                x2, y2 = int(p2["left"]+p2["radius"]), int(p2["top"]+p2["radius"])
                code += f"cv2.line(img, ({x1}, {y1}), ({x2}, {y2}), {color_bgr}, {stroke})\n"
            st.code(code, language="python")
        elif len(points) == 1: st.info("📍 Marca el destino.")
    else:
        code = ""
        for obj in objects:
            if obj["type"] == "rect":
                x1, y1 = int(obj["left"]), int(obj["top"])
                x2, y2 = int(x1 + obj["width"]), int(y1 + obj["height"])
                code += f"cv2.rectangle(img, ({x1}, {y1}), ({x2}, {y2}), {color_bgr}, {stroke})\n"
            elif obj["type"] == "circle":
                cx, cy = int(obj["left"]+obj["radius"]), int(obj["top"]+obj["radius"])
                r = int(obj["radius"])
                code += f"cv2.circle(img, ({cx}, {cy}), {r}, {color_bgr}, {stroke})\n"
        st.code(code, language="python")