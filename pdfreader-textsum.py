import streamlit as st
import sqlite3
from hashlib import sha256
from transformers import pipeline
from PyPDF2 import PdfFileReader

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

# Function to summarize text using transformers pipeline
def summarize_text(text, max_words):
    summarizer = pipeline("summarization")
    max_length = min(max_words, 512)  # Ensure the max length does not exceed model capabilities
    min_length = max(30, int(max_length / 4))  # Set a minimum length based on max length
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
    return summary

# Function to read text from a specified range of pages in a PDF
def read_pdf_range(uploaded_file, start_page, end_page):
    reader = PdfFileReader(uploaded_file)
    text = ""
    for page_num in range(start_page - 1, end_page):
        if page_num < reader.numPages:
            text += reader.getPage(page_num).extract_text()
    return text

# Main function to run the Streamlit web app
def main():
    st.set_page_config(page_title="Your Read-Mate", page_icon=":books:", layout="wide")
    st.title("Your Read-Mate")

    # Initialize SQLite connection and cursor
    conn, c = initialize()

    # Check if logged in
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Creating a header with login/signup options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col3:
        if not st.session_state.logged_in:
            if st.button("Login", key="login"):
                st.session_state.show_login = True
                st.session_state.show_signup = False

            if st.session_state.get("show_login"):
                with st.expander("Login", expanded=True):
                    login()

            if st.button("Sign Up", key="signup"):
                st.session_state.show_signup = True
                st.session_state.show_login = False

            if st.session_state.get("show_signup"):
                with st.expander("Sign Up", expanded=True):
                    sign_up()

        else:
            st.write(f"Logged in as {st.session_state.user[1]}")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.success("You have logged out successfully")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Text Summarizer"):
            st.session_state.active_page = "Text Summarizer"
        if st.button("PDF Reader"):
            st.session_state.active_page = "PDF Reader"

    if st.session_state.get("active_page") == "Text Summarizer":
        if st.session_state.logged_in:
            st.header("Text Summarizer")
            text = st.text_area("Enter text to summarize")
            max_words = st.number_input("Enter the number of words for the summary", min_value=10, value=50)
            if st.button("Summarize"):
                if text:
                    summary = summarize_text(text, max_words)
                    st.subheader("Summary")
                    st.write(summary)
                else:
                    st.warning("Please enter some text to summarize.")
        else:
            st.warning("Please log in to access the functionalities")

    elif st.session_state.get("active_page") == "PDF Reader":
        if st.session_state.logged_in:
            st.header("PDF Reader")
            uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
            if uploaded_file is not None:
                start_page = st.number_input("Enter starting page number", min_value=1, value=1)
                end_page = st.number_input("Enter ending page number", min_value=1, value=1)

                if start_page > end_page:
                    st.error("Starting page number should be less than or equal to ending page number.")
                elif st.button("Read Pages"):
                    st.subheader(f"PDF Content (Pages {start_page} to {end_page})")
                    pdf_text = read_pdf_range(uploaded_file, start_page, end_page)
                    st.write(pdf_text)
        else:
            st.warning("Please log in to access the functionalities")

# Function to handle user sign-up
def sign_up():
    email = st.text_input("Email", key="signup_email")
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
    
    if st.button("Sign Up", key="signup_button"):
        if password == confirm_password:
            add_user(username, email, password)
        else:
            st.error("Passwords do not match")

# Function to handle user login
def login():
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login", key="login_button"):
        user = check_user(email, password)
        if user:
            st.success(f"Welcome {user[1]}!")
            st.session_state.logged_in = True
            st.session_state.user = user
        else:
            st.error("Invalid email or password")

if __name__ == "__main__":
    main()
