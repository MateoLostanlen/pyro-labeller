import os

import streamlit as st
from cvat_manager import create_user
from dotenv import load_dotenv
from utils import nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

load_dotenv(".env")
cvat_url = os.environ.get("HOST")

st.image("logo.png", use_column_width=True)

st.subheader("💻 On va te rediriger vers un logiciel open-source pour labeliser des images")

email = st.text_input(
    """On a besoin de ton adresse mail pour créer un compte utilisateur (pas de spam, promis !).
     Entre le dans la ci-dessous puis cliquez sur entrée"""
)

if email:
    st.write(
        """Voici tes identifiants, note les bien pour accéder à la plateforme.
         Tu peux utiliser ton email ou ton username comme login"""
    )
    (username, password) = create_user(email)
    if password is None:
        st.write(username)
    else:
        st.write("username: ", username)
        st.write("password: ", password)

        st.write(f"Tu peux acceder à l'outil de labelisation [ici]({cvat_url})")

    if st.button("Labélisation terminée", use_container_width=True):
        nav_page("thanks")

if not email:

    if st.button("Entrée", use_container_width=True):
        a = 1
