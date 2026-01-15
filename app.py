import streamlit as st
from PIL import Image, ImageOps
import xml.etree.ElementTree as ET
import math
import io

st.set_page_config(page_title="SVG Pattern Tool", layout="wide")

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

st.title("🎨 Vector Pattern Halftone Tool")

# --- Боковая панель (Настройки) ---
st.sidebar.header("1. Загрузка данных")
uploaded_img = st.sidebar.file_uploader("Загрузите фото", type=["png", "jpg", "jpeg"])
uploaded_pats = st.sidebar.file_uploader("Загрузите паттерны (SVG)", type=["svg"], accept_multiple_files=True)

st.sidebar.header("2. Настройки")
mode = st.sidebar.selectbox("Режим раскладки", ["Сетка (Grid)", "Спираль (Spiral)"])
density = st.sidebar.slider("Плотность", 10, 150, 60)
max_scale = st.sidebar.slider("Макс. масштаб", 0.1, 2.5, 1.0)
min_scale = st.sidebar.slider("Мин. масштаб", 0.0, 1.0, 0.0)
invert = st.sidebar.checkbox("Инвертировать яркость")

# --- Логика генерации ---
if uploaded_img and uploaded_pats:
    img = Image.open(uploaded_img).convert("L")
    if invert: img = ImageOps.invert(img)
    w, h = img.size
    
    p_data = [extract_svg_paths(f) for f in uploaded_pats]
    p_data = [p for p in p_data if p is not None]

    # Генерация точек
    points = []
    if mode == "Сетка (Grid)":
        cols = density
        rows = int(cols * (h / w))
        cell_size = 1.0 / cols
        for y in range(rows):
            for x in range(cols):
                points.append(((x + 0.5)/cols, (y + 0.5)/rows))
    else:
        count = density * 25
        cell_size = 1.8 / math.sqrt(count)
        for i in range(count):
            r = math.sqrt(i / count) / 2
            theta = i * math.pi * (3 - math.sqrt(5))
            points.append((0.5 + r * math.cos(theta), 0.5 + r * math.sin(theta)))

    # Сборка SVG
    view_box = 2000
    cell_px = view_box * cell_size
    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_box} {view_box}" fill="black">']
    svg_parts.append('<rect width="100%" height="100%" fill="white" />')

    for nx, ny in points:
        px_x, px_y = int(nx * (w-1)), int(ny * (h-1))
        brightness = img.getpixel((px_x, px_y))
        if brightness > 252: continue
        
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

    # --- Отображение ---
    col1, col2 = st.columns(2)
    with col1:
        st.image(uploaded_img, caption="Оригинал", use_container_width=True)
    with col2:
        st.write("Превью результата (SVG):")
        st.components.v1.html(final_svg, height=600)
        
    st.download_button("Скачать готовый SVG", final_svg, file_name="pattern.svg", mime="image/svg+xml")
else:
    st.info("Пожалуйста, загрузите изображение и хотя бы один SVG-паттерн в боковой панели.")