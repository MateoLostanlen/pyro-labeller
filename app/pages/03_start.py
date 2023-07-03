import os

import streamlit as st
from cvat_manager import create_user
from dotenv import load_dotenv
from utils import nav_page

# Initialization
if "done" not in st.session_state:
    st.session_state["done"] = False

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

load_dotenv(".env")
cvat_url = os.environ.get("HOST")

st.image("logo.png", use_column_width=True)

st.subheader("💻 On va te rediriger vers un logiciel open-source pour labeliser des images")

if st.button("Générer des identifiants, ca peut prendre quelques secondes ⏳", use_container_width=True):

    st.write(
        """Voici tes identifiants, note les bien pour accéder à la plateforme.
         Tu peux utiliser ton email ou ton username comme login"""
    )
    (username, password) = create_user()
    if password is None:
        st.write(username)
    else:
        st.write("username: ", username)
        st.write("password: ", password)

        st.write(f"Tu peux acceder à l'outil de labelisation [ici]({cvat_url})")
        st.session_state["done"] = False


if st.session_state["done"]:
    if st.button("Labélisation terminée ? Clic ici pour passer à la page suivante", use_container_width=True):
        nav_page("thanks")
