import streamlit as st
from utils import nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)

st.subheader("👀 On a besoin de tes yeux pour détecter des départs de feux")

st.write("#### 15 minutes de ton temps pour lutter contre les incendies")

st.write("Grâce à toi et à des centaines d’autres contributeurs, l’ONG [Pyronear](https://pyronear.org/) pourra améliorer son algorithme de détection et alerter le plus vite possible les pompiers quand un feu se déclare.")


if st.button("Détecter des feux", use_container_width=True):
    nav_page("tuto_video")


