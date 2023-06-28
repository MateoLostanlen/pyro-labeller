import streamlit as st
from utils import nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)

st.subheader("📄 On t’a préparé un pack labélisateur qui résume toutes les étapes")

url = (
    "https://bayesimpact.notion.site/"
    "D-tecter-des-d-parts-de-feux-avec-Pyronear-b2e9b50b7ceb4a50b2870622096b58cd?pvs=4"
    ""
)
st.write(f"Clique sur [ce lien]({url}) pour y accéder ")


if st.button("Commencer la labélisation d'images", use_container_width=True):
    nav_page("start")
