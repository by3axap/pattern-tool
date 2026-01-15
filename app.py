import streamlit as st
from PIL import Image, ImageOps
import xml.etree.ElementTree as ET
import random
import io

# Настройки страницы
st.set_page_config(page_title="SVG Pattern Tool", layout="wide")

# Инициализация состояния для рандомизации
if 'rand_seed' not in st.session_state:
    st.session_state.rand_seed = 42

def change_seed():
    st.session_state.rand_seed = random.randint(0, 10000)

# CSS для светлого минималистичного интерфейса
st.markdown("""
    <style>
    .stApp { background-color: #f8f8f8; }
    section[data-testid="stSidebar"] { background-color: #efefef !important; border-right: 1px solid #ddd; }
    h1, h2, h3, p, label { 
        font-family: 'Monaco', 'Consolas', monospace !important; 
        color: #333 !important; text-transform: uppercase; font-size: 13px !important; 
    }
    .stButton>button {
        width: 100%; border-radius: 0px; background-color: #333 !important;
        color: white !important; border: none; padding: 10px; font-family: monospace;
    }
    /* Стиль для превью */
    .svg-container {
        background: white;
        border: 1px solid #ddd;
        padding: 10px;
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

# --- Сайдбар ---
with st.sidebar:
    st.write("### Upload media")
    uploaded_img = st.file_uploader("Image", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    st.write("---")
    st.write("### Upload patterns")
    uploaded_pats = st.file_uploader("SVGs", type=["svg"], accept_multiple_files=True, label_visibility="collapsed")
    
    st.write("---")
    density = st.slider("Grid Density", 10, 200, 60)
    max_scale = st.slider("Max Scale", 0.1, 4.0, 1.2)
    
    st.write("### Randomness")
    jitter = st.slider("Position Jitter", 0.0, 1.0, 0.1)
    rotate = st.checkbox("Random Rotation", value=True)
    st.button("RANDOMISE POSITION", on_click=change_seed)
    
    st.write("---")
    invert = st.checkbox("Invert Colors", value=False)

# --- Логика ---
if uploaded_img and uploaded_pats:
    # Фиксируем случайность сидом из session_state
    random.seed(st.session_state.rand_seed)
    
    img = Image.open(uploaded_img).convert("L")
    if invert: img = ImageOps.invert(img)
    w_orig, h_orig = img.size
    
    # Расчет пропорций
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
                # Поиск яркости в соответствующей точке фото
                px_x = int((x / cols) * (w_orig - 1))
                px_y = int((y / rows) * (h_orig - 1))
                brightness = img.getpixel((px_x, px_y))
                
                if brightness > 252: continue
                
                darkness = 1.0 - (brightness / 255.0)
                final_scale = max_scale * darkness
                if final_scale < 0.05: continue
                
                # Выбор паттерна
                p_idx = int((brightness / 255.0) * len(p_data))
                curr_p = p_data[min(p_idx, len(p_data)-1)]
                
                # Расчет координат с учетом рандомизации (Jitter)
                shift_x = (random.random() - 0.5) * cell_px * jitter
                shift_y = (random.random() - 0.5) * cell_px * jitter
                
                draw_sz = cell_px * final_scale
                tx = (x + 0.5) * cell_px - draw_sz/2 + shift_x
                ty = (y + 0.5) * cell_px - draw_sz/2 + shift_y # используем cell_px для сохранения квадратности ячейки
                
                # Вращение
                angle = random.randint(0, 360) if rotate else 0
                center_p = draw_sz / 2
                
                v_box = [float(v) for v in curr_p['viewBox'].split()]
                s_factor = draw_sz / (v_box[2] if v_box[2] != 0 else 100)
                
                transform = f'translate({tx:.2f}, {ty:.2f}) scale({s_factor:.4f})'
                if rotate:
                    # Поворот вокруг центра паттерна
                    transform += f' rotate({angle}, {v_box[2]/2}, {v_box[3]/2})'
                
                svg_parts.append(f'<g transform="{transform}">{curr_p["inner"]}</g>')

        svg_parts.append('</svg>')
        final_svg = "".join(svg_parts)

        # Вывод результата
        st.components.v1.html(f"<div class='svg-container'>{final_svg}</div>", height=800)
        
        st.download_button(
            label="EXPORT CANVAS (SVG)",
            data=final_svg,
            file_name="pro_pattern_output.svg",
            mime="image/svg+xml"
        )
else:
    st.markdown("<div style='border:1px solid #ddd; height:400px; display:flex; align-items:center; justify-content:center; background:white;'><p style='color:#999;'>Awaiting media...</p></div>", unsafe_allow_html=True)
