import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from utils import nav_page


def get_credentials():
    df = pd.read_csv("data/task_database.csv", index_col=0)
    df_free = df.loc[df["assign_time"].isnull()]
    if len(df_free) > 0:
        data = df_free.iloc[0]
        df.loc[df["username"] == data.username, ["assign_time"]] = datetime.now()
        if data.username != "username":
            df.to_csv("data/task_database.csv")
            return data.username, data.password

    return None, None


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

st.write(
    """Nous utilisons [CVAT](https://www.cvat.ai/) pour réaliser l’annotation, le seul navigateur officiellement
    supporté par CVAT est Google Chrome, nous te recommandons de l’utiliser pour une expérience plus fluide."""
)

if st.button("Générer des identifiants, ca peut prendre quelques secondes ⏳", use_container_width=True):

    (username, password) = get_credentials()
    if password is None:
        st.write(f"Il n'y a plus de tâche d'annotation disponible, merci de réessayer plus tard")
    else:
        st.write("Voici tes identifiants, note les bien pour accéder à la plateforme :")
        st.write("username: ", username)
        st.write("password: ", password)

        st.write(f"Tu peux acceder à l'outil de labelisation [ici]({cvat_url}/jobs?page=1)")
        st.session_state["done"] = False


if st.session_state["done"]:
    if st.button("Labélisation terminée ? Clic ici pour passer à la page suivante", use_container_width=True):
        nav_page("thanks")
