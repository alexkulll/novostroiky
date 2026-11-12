from pathlib import Path
import streamlit as st
from selection import ROOT


def render_photo(row, show_placeholder=False):
    image = (ROOT / row['photo_path']).resolve()
    if image.is_relative_to(ROOT) and image.is_file():
        st.image(str(image), use_container_width=True)
    elif show_placeholder:
        st.caption('Изображение появится здесь')


def render_details(row, key_prefix, show_on_map=None, *, heading=False, estimate=None):
    if heading:
        st.subheader(row['complex_name'])
    if estimate is not None:
        st.write(f"**≈ {estimate:,} ₽**".replace(',', ' '))
    st.write(row['district_address'])
    st.write(f"{row['developer']} · {row['class']}-класс")
    st.write(f"От {row['price_per_sqm']:,} ₽/м²".replace(',', ' '))
    st.write('Срок сдачи: ' + row['completion'])
    if row['source_url'].startswith(('https://', 'http://')):
        st.link_button('Источник ↗', row['source_url'], key=f"{key_prefix}_source_{row['id']}")
    if show_on_map:
        st.button('Посмотреть на карте ↓', key=f"{key_prefix}_map_{row['id']}", on_click=show_on_map, args=(row['city'], row['id']), use_container_width=True)
