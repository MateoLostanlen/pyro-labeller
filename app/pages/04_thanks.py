import streamlit as st
from utils import get_ip

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)


st.subheader("💪 Un grand merci pour ta participation !")

url = f"http://{get_ip()}:8501/#on-a-besoin-de-tes-yeux-pour-d-tecter-des-d-parts-de-feux"
st.write(f"N’hésite pas à partager [l’initiative]({url}) à tes proches")


st.subheader("☝️ Tu es dispo 15 minutes de plus ?")

st.write("Clique à nouveau sur [ce lien]({cvat_url}) pour labeliser d’autres images")

