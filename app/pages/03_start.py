import streamlit as st
from utils import get_ip, nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

st.image("logo.png", use_column_width=True)

st.subheader("💻 On va te rediriger vers un logiciel open-source pour labeliser des images")

email = st.text_input("On a besoin de ton adresse mail pour créer un compte utilisateur (pas de spam, promis !). Entre le dans la ci-dessous puis cliquez sur entrée")

if email:
    st.write(
        """Voici tes identifiants, note les bien pour accéder à la plateforme.
         Tu peux utiliser ton email ou ton username comme login"""
    )
    st.write("email: ", email)
    st.write("username: ", email)
    st.write("password: ", email)

    cvat_url = f"http://{get_ip()}:8080"
    st.write(f"Tu peux acceder à l'outil de labelisation [ici]({cvat_url})")


    if st.button("Labélisation terminée", use_container_width=True):
        nav_page("thanks")
