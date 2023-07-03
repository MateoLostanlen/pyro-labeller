import os

import streamlit as st
from dotenv import load_dotenv
from utils import get_ip

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)


st.subheader("💪 Un grand merci pour ta participation !")

url = f"http://{get_ip()}:8501/#on-a-besoin-de-tes-yeux-pour-d-tecter-des-d-parts-de-feux"

st.write("N'hésite pas à partager l'initiative à tes proches en copiant-collant le message ci-après :")
st.write(
    f"""Tu as un ordi et 15mn de dispo ? L'ONG [Pyronear](https://pyronear.org/) a besoin de tes yeux pour
détecter des départs de feux et alerter les pompiers dès que possible. Rdv sur ce [lien]({url})"""
)

load_dotenv(".env")
cvat_url = os.environ.get("HOST")

st.subheader("☝️ Tu es dispo 15 minutes de plus ?")
st.write(f"Clique à nouveau sur [ce lien]({cvat_url}) pour labeliser d’autres images")
