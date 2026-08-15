# python -m streamlit run app.py

import streamlit as st

st.title("Study Question Bank")

question = st.text_input("Question")
answer_url = st.text_input("Answer URL")
topic = st.text_input("Topic")

st.subheader("Questions")

