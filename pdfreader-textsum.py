import streamlit as st
import sqlite3
from hashlib import sha256
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, DirectoryLoader
from transformers import T5Tokenizer, T5ForConditionalGeneration, pipeline
import torch
import base64
from gtts import gTTS
import os

# Initialize SQLite connection and cursor
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create users table if it doesn't exist
c.execute('''
          CREATE TABLE IF NOT EXISTS users
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT,
          email TEXT UNIQUE,
          password TEXT)
          ''')
conn.commit()

# Function to hash passwords
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# Function to add a user to the SQLite database
def add_user(username, email, password):
    c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
              (username, email, hash_password(password)))
    conn.commit()
    st.success("You have successfully signed up!")

# Function to check if a user exists in the SQLite database
def check_user(email, password):
    c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, hash_password(password)))
    return c.fetchone()

# Function to initialize SQLite connection and create tables if needed
def initialize():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS users
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT,
              email TEXT UNIQUE,
              password TEXT)
              ''')
    conn.commit()
    return conn, c

# Model and tokenizer
checkpoint = "MBZUAI/LaMini-Flan-T5-248M"
tokenizer = T5Tokenizer.from_pretrained(checkpoint)
base_model = T5ForConditionalGeneration.from_pretrained(checkpoint)

# File loader and tokenizing
def file_preprocessing(file):
    loader = PyPDFLoader(file)
    pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
    texts = text_splitter.split_document(pages)
    final_texts = ""
    for text in texts:
        final_texts += text.page_content()
    return final_texts

# Summarization pipeline setup
def llm_pipeline(filepath):
    pipe_sum = pipeline(
        'summarization', 
        model=base_model,
        tokenizer=tokenizer,
        device=0 if torch.cuda.is_available() else -1,  # Use GPU if available
        framework='pt'  # Use PyTorch framework
    )
    input_text = file_preprocessing(filepath)
    result = pipe_sum(input_text)
    result = result[0]['summary_text']
    return result 

# Streamlit configuration
st.set_page_config(layout='wide', page_title="Your Read Mate")

# Main function to run Streamlit app
def main():
    st.title("Enabling AI to increase your productivity")

    # Initialize SQLite connection and cursor
    conn, c = initialize()

    # Login form
    logged_in = False
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        user_data = check_user(email, password)
        if user_data:
            st.sidebar.success(f"Logged in as {user_data[1]}")
            logged_in = True
        else:
            st.sidebar.error("Invalid email or password")

    # Signup form
    if not logged_in:
        st.sidebar.subheader("Sign Up")
        new_username = st.sidebar.text_input("New Username")
        new_email = st.sidebar.text_input("New Email")
        new_password = st.sidebar.text_input("New Password", type="password")

        if st.sidebar.button("Sign Up"):
            add_user(new_username, new_email, new_password)

    # Main content
    uploaded_file = st.file_uploader("Upload Your PDF File", type=['pdf'])

    if uploaded_file is not None:
        displaypdf(uploaded_file)

        if st.button("Summarize") and logged_in:
            col1, col2 = st.columns(2)
            filepath = "data/" + uploaded_file.name
            with open(filepath, 'wb') as temp_file:
                temp_file.write(uploaded_file.read())

            with col1:
                st.info("Uploaded pdf file")
                pdf_viewer = displaypdf(filepath)

            with col2:
                st.info("Summarized Text below")

                summary = llm_pipeline(filepath)
                st.success(summary)

                # Add voice output using gTTS
                st.audio("data:audio/mp3;base64," + base64.b64encode(text_to_speech(summary).read()).decode("utf-8"))

# Function to display PDF
@st.cache_data
def displaypdf(file):
    with open(file.name, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')

    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# Function to convert text to speech
def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    return tts

if __name__ == '__main__':
    main()


