import streamlit as st
from utils import nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)

st.subheader("🎥 Clique sur play pour savoir comment détecter des départs de feux")

st.write(
    """On va te soumettre des images sur lesquelles tu pourras repérer des fumées.
     On appelle cela la “labélisation” d’images."""
)

st.video("https://youtu.be/9LZ7qygC9ic")

if st.button("J’ai visionné la vidéo", use_container_width=True):
    nav_page("doc")
