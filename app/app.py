import glob

import streamlit as st
from utils import nav_page

st.set_page_config(
    page_title="Pyronear Annotation Tool",
    page_icon="👋",
)

# Count labels
label_files = glob.glob("data/labels/**/obj_train_data/*.txt")
# nb_wf = 0
# for file in label_files:
#     with open(file) as f:
#         lines = f.readlines()
#     nb_wf += len(lines)

st.image("logo.png", use_column_width=True)

st.subheader("👀 On a besoin de tes yeux pour détecter des départs de feux")

st.write("#### 15 minutes de ton temps pour lutter contre les incendies")

st.write(
    f"""[Pyronear](https://pyronear.org/) s’est donné pour mission de créer une solution open source de détection détection précoce, performante,
 automatique, énergiquement sobre, économique et modulable des départs de feux dans les espaces naturels.
Grâce à toi et à des centaines d’autres contributeurs nous allons améliorer notre algorithme de détection,
nous avons déjà annoté :
"""
)

col1, col2 = st.columns(2)
col1.metric("Images", len(label_files), delta=None, delta_color="normal", help=None, label_visibility="visible")
# col2.metric("Images avec un feu", nb_wf, delta=None, delta_color="normal", help=None, label_visibility="visible")

if st.button("Détecter des feux", use_container_width=True):
    nav_page("tuto_video")
