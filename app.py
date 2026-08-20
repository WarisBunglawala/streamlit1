import streamlit as st
from datetime import datetime

st.title("Hi Streamlit App")
st.write("Hi")
st.write("Current date and time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
