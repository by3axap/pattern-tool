import streamlit as st
from PIL import Image, ImageOps
import xml.etree.ElementTree as ET
import math
import io

# Настройки страницы
st.set_page_config(page_title="SVG Pattern Tool", layout="wide")

# Внедряем CSS для изменения интерфейса под ваш референс
st.markdown("""
    <style>
    /* Общий фон страницы */
    .stApp {
        background-color: #f8f8f8;
    }
    
    /* Боковая панель */
    section[data-testid="stSidebar"] {
        background-color: #efefef !important;
        border-right: 1px solid #ddd;
    }
    
    /* Шрифты и заголовки */
    h1, h2, h3, p, label {
        font-family: 'Monaco', 'Consolas', monospace !important;
        color: #333 !important;
        text-transform: uppercase;
        font-size: 14px !important;
    }

    /* Стилизация слайдеров */
    .stSlider [data-baseweb="slider"] {
        margin-top: 10px;
    }

    /* Стилизация кнопок */
    .stButton>button {
        width: 100%;
        border-radius: 0px;
        background-color: #333 !important;
        color: white !important;
        border: none;
        padding: 10px;
        font-family: monospace;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #555 !important;
    }

    /* Убираем лишние отступы сверху */
    .block-container {
        padding-top: 2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

def extract_svg_paths(file):
    try:
        content = file.read().decode("utf-8")
        root = ET.fromstring(content)
        viewbox = root.attrib.get('viewBox')
        if not viewbox:
            w = root.attrib.get('width', '100').replace('px', '')
            h = root.attrib.get('height', '100').replace('px', '')
            viewbox = f"0 0 {w} {h}"
        
        start = content.find('>') + 1
        end = content.rfind('</svg>')
        return {'inner': content[start:end], 'viewBox': viewbox}
    except: return None

# --- Боковая панель (Сайдбар) ---
with st.sidebar:
    st.write("### Upload media")
    uploaded_img = st.file_uploader("Choose image", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    st.write("---")
    st.write("### Upload patterns")
    uploaded_pats = st.file_uploader("Choose SVGs", type=["svg"], accept_multiple_files=True, label_visibility="collapsed")
    
    st.write("---")
    mode = st.selectbox("Layout Mode", ["Grid", "Spiral"])
    density = st.slider("Grid Density", 10, 200, 60)
    max_scale = st.slider("Max Scale", 0.1, 3.0, 1.0)
    min_scale = st.slider("Min Scale", 0.0, 1.0, 0.0)
    invert = st.checkbox("Invert Colors", value=False)

# --- Основная логика ---
if uploaded_img and uploaded_pats:
    img = Image.open(uploaded_img).convert("L")
    if invert: img = ImageOps.invert(img)
    w, h = img.size
    
    p_data = [extract_svg_paths(f) for f in uploaded_pats]
    p_data = [p for p in p_data if p is not None]

    if not p_data:
        st.warning("Please upload valid SVG patterns.")
    else:
        # Генерация точек
        points = []
        if mode == "Grid":
            cols = density
            rows = int(cols * (h / w))
            cell_size = 1.0 / cols
            for y in range(rows):
                for x in range(cols):
                    points.append(((x + 0.5)/cols, (y + 0.5)/rows))
        else:
            count = density * 20
            cell_size = 1.8 / math.sqrt(count)
            for i in range(count):
                r = math.sqrt(i / count) / 2
                theta = i * math.pi * (3 - math.sqrt(5))
                points.append((0.5 + r * math.cos(theta), 0.5 + r * math.sin(theta)))

        # Сборка SVG
        view_box = 2000
        cell_px = view_box * cell_size
        svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_box} {view_box}" width="100%" height="100%">']
        svg_parts.append('<rect width="100%" height="100%" fill="white" />')

        for nx, ny in points:
            px_x, px_y = int(nx * (w-1)), int(ny * (h-1))
            brightness = img.getpixel((px_x, px_y))
            if brightness > 250: continue
            
            darkness = 1.0 - (brightness/255.0)
            final_scale = min_scale + (max_scale - min_scale) * darkness
            if final_scale < 0.05: continue
            
            p_idx = int((brightness/255.0) * len(p_data))
            curr_p = p_data[min(p_idx, len(p_data)-1)]
            
            draw_sz = cell_px * final_scale
            tx, ty = nx * view_box - draw_sz/2, ny * view_box - draw_sz/2
            
            v_box = [float(v) for v in curr_p['viewBox'].split()]
            s_factor = draw_sz / (v_box[2] if v_box[2] != 0 else 100)
            
            svg_parts.append(f'<g transform="translate({tx:.2f}, {ty:.2f}) scale({s_factor:.4f})">{curr_p["inner"]}</g>')

        svg_parts.append('</svg>')
        final_svg = "".join(svg_parts)

        # Вывод результата на весь экран
        st.components.v1.html(final_svg, height=800, scrolling=True)
        
        # Кнопка скачивания в стиле референса
        st.download_button(
            label="EXPORT CANVAS (SVG)",
            data=final_svg,
            file_name="halftone_output.svg",
            mime="image/svg+xml"
        )
else:
    # Заглушка, когда файлы не выбраны
    st.markdown("""
        <div style='border: 2px dashed #ccc; height: 400px; display: flex; align-items: center; justify-content: center;'>
            <p style='color: #999; font-family: monospace;'>Upload image and patterns to start generation</p>
        </div>
    """, unsafe_allow_html=True)
