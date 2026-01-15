import streamlit as st
from PIL import Image, ImageOps
import xml.etree.ElementTree as ET
import math

# Конфигурация страницы
st.set_page_config(page_title="SVG Halftone Pro", layout="wide")

# Минималистичный интерфейс (Light UI)
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    section[data-testid="stSidebar"] { 
        background-color: #f2f2f2 !important; 
        border-right: 1px solid #e0e0e0; 
    }
    * { font-family: 'Monaco', 'Consolas', monospace !important; }
    h3 { font-size: 12px !important; letter-spacing: 1px; color: #666 !important; text-transform: uppercase; }
    label p { font-size: 11px !important; color: #888 !important; text-transform: uppercase; }

    .stButton>button {
        width: 100%; border-radius: 2px; background-color: #1a1a1a !important;
        color: #ffffff !important; border: none; padding: 12px; font-size: 12px !important;
        text-transform: uppercase;
    }
    
    .svg-canvas {
        background-color: #ffffff; border: 1px solid #eee;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)

def extract_svg_paths(file):
    try:
        content = file.read().decode("utf-8")
        root = ET.fromstring(content)
        vbox = root.attrib.get('viewBox')
        if not vbox:
            w = root.attrib.get('width', '100').replace('px', '')
            h = root.attrib.get('height', '100').replace('px', '')
            vbox = f"0 0 {w} {h}"
        start = content.find('>') + 1
        end = content.rfind('</svg>')
        return {'inner': content[start:end], 'viewBox': vbox}
    except: return None

# --- САЙДБАР ---
with st.sidebar:
    st.write("### 1. Media")
    uploaded_img = st.file_uploader("Image", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    st.write("### 2. Patterns")
    uploaded_pats = st.file_uploader("SVGs", type=["svg"], accept_multiple_files=True, label_visibility="collapsed")
    
    st.write("---")
    st.write("### 3. Grid settings")
    density = st.slider("Density", 20, 250, 80)
    max_scale = st.slider("Max Scale", 0.1, 5.0, 1.5)
    
    st.write("---")
    st.write("### 4. Perspective")
    # Ползунки перспективы
    persp_x = st.slider("Perspective X", -1.0, 1.0, 0.0, step=0.05)
    persp_y = st.slider("Perspective Y", -1.0, 1.0, 0.0, step=0.05)
    
    st.write("---")
    invert = st.checkbox("Invert Image", value=False)
    st.write("---")

# --- ЛОГИКА ОБРАБОТКИ ---
if uploaded_img and uploaded_pats:
    img = Image.open(uploaded_img).convert("L")
    if invert: img = ImageOps.invert(img)
    w_orig, h_orig = img.size
    
    aspect_ratio = h_orig / w_orig
    view_box_w = 2000
    view_box_h = int(view_box_w * aspect_ratio)
    
    p_data = [extract_svg_paths(f) for f in uploaded_pats]
    p_data = [p for p in p_data if p is not None]

    if p_data:
        cols = density
        rows = int(cols * aspect_ratio)
        cell_px = view_box_w / cols
        
        svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_box_w} {view_box_h}" width="100%" height="auto">']
        svg_parts.append('<rect width="100%" height="100%" fill="white" />')

        for y in range(rows):
            for x in range(cols):
                # Базовые нормализованные координаты (0.0 - 1.0)
                nx = x / cols
                ny = y / rows
                
                # ПРИМЕНЕНИЕ ПЕРСПЕКТИВЫ
                # Смещаем центр в 0, чтобы искажение шло от середины
                dx = nx - 0.5
                dy = ny - 0.5
                
                # Математика искажения: меняем масштаб осей в зависимости от положения другой оси
                # Это создает эффект "схождения" линий к горизонту
                factor_x = 1.0 + (persp_x * dy)
                factor_y = 1.0 + (persp_y * dx)
                
                distorted_nx = 0.5 + (dx * factor_x)
                distorted_ny = 0.5 + (dy * factor_y)
                
                # Проверка, чтобы точка не вылетела за границы (опционально)
                if not (0 <= distorted_nx <= 1 and 0 <= distorted_ny <= 1):
                    continue

                # Поиск яркости по оригинальным координатам (чтобы картинка не плыла мимо сетки)
                px_x = int(nx * (w_orig - 1))
                px_y = int(ny * (h_orig - 1))
                brightness = img.getpixel((px_x, px_y))
                
                if brightness > 252: continue
                
                darkness = 1.0 - (brightness / 255.0)
                
                # Размер паттерна также может зависеть от перспективы (эффект удаления)
                persp_scale_factor = (factor_x + factor_y) / 2
                final_scale = max_scale * darkness * persp_scale_factor
                
                if final_scale < 0.01: continue
                
                # Выбор паттерна
                p_idx = int((brightness / 255.0) * (len(p_data) - 1))
                curr_p = p_data[p_idx]
                
                draw_sz = cell_px * final_scale
                tx = distorted_nx * view_box_w - draw_sz/2
                ty = distorted_ny * view_box_h - draw_sz/2
                
                v_box = [float(v) for v in curr_p['viewBox'].split()]
                s_factor = draw_sz / v_box[2]
                
                svg_parts.append(f'<g transform="translate({tx:.2f}, {ty:.2f}) scale({s_factor:.4f})">{curr_p["inner"]}</g>')

        svg_parts.append('</svg>')
        final_svg = "".join(svg_parts)

        # Отображение
        st.components.v1.html(f"""
            <div style="display: flex; justify-content: center; padding: 20px; background: #fcfcfc;">
                <div style="width: 100%; max-width: 850px; background: white; border: 1px solid #eee; padding: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.06);">
                    {final_svg}
                </div>
            </div>
        """, height=850)
        
        st.sidebar.write("---")
        st.sidebar.download_button("EXPORT SVG", final_svg, "halftone_perspective.svg", "image/svg+xml")
else:
    st.markdown("<div style='border:1px dashed #ccc; height:400px; display:flex; align-items:center; justify-content:center; background:white; color:#bbb; font-family:monospace;'>Awaiting image and patterns...</div>", unsafe_allow_html=True)
