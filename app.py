import streamlit as st
import openai
import pandas as pd
import hashlib
import os
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.cosmos import CosmosClient, PartitionKey
import logging
from dotenv import load_dotenv
from grader import syntax_check

# Securely load environment variables
load_dotenv()
url = os.environ['COSMOS_DB_URL']  # Cosmos DB URL
database_name = os.environ['COSMOS_DB_DATABASE']  # Database name
azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY')
azure_openai_model = os.environ.get('AZURE_OPENAI_MODEL')
azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')

openai.api_version = "2023-05-15"
openai.api_type = "azure"
openai.api_key = azure_openai_api_key
openai.api_base = azure_openai_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """
You are an auto grader for web programing courses. You will be given the student codes, compilation results and rubric as well as extra information if any. 
Fill out the rubric and provide justification for your grading. Refer to the line number with error when possible. Always show the achieved score in bold number. Never add up the total grade or do any math. Example:
'1. {First rubric item} [Score:{First item score}] .\n- **Score: 1/1** {Justification and reasoning}\n\n
2. {Second rubric item} [Score:{Second item score}]\n- **Score: 2/3** {Justification and reasoning}\n\n
3. {Third rubric item} [Score:{Third item score}]\n- **Score: 3/3** {Justification and reasoning}\n\n
Provide extra information afterward when aplicable, like compile error, instructor tips to grade manual grade this submission, student feedback etc.\n
User input start now:
"""

CHAPTER_DICT = {
    "Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e": ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    "Minnick Responsive Web Design with HTML 5 and CSS, 9e": ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    }

EXERCISE_DICT = {
    "Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e": {
        "1":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "2":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "3":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "4":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "5":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "6":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "7":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "8":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "9":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"],
        "10":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "ex05", "rw01"]},
    "Minnick Responsive Web Design with HTML 5 and CSS, 9e": {
        "1":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "2":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "3":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "4":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "5":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "6":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "7":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "8":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "9":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "10":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "11":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"],
        "12":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"]}
    }

def fetch_prompt(book_title, chapter, exercise):
    # Azure Cosmos DB configuration
    
    key = os.environ['COSMOS_DB_KEY']  # Cosmos DB primary key
    container_name = os.environ['COSMOS_DB_PROMPT_CONTAINER']  # Container name

    try:
        # Create a Cosmos client
        client = CosmosClient(url, credential=key)

        # Select the database and container
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)

        # Query to fetch the exercise
        query = "SELECT * FROM c WHERE c.title=@book_title AND c.chapter=@chapter AND c.ex=@exercise"
        parameters = [
            {"name": "@book_title", "value": book_title},
            {"name": "@chapter", "value": chapter},
            {"name": "@exercise", "value": exercise}
        ]
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        if items:
            return items[0]
        else:
            return None

    except CosmosHttpResponseError as e:
        logging.error("Cosmos DB error: %s", str(e))
        return None, None

def grade_submission(file, prompt):
    try:
        grading_reports, raw_file_texts = syntax_check(file)

        messages=[{"role": "system", "content": SYSTEM_PROMPT}]
        
        messages.append({"role": "user", "content": "You are grading the following file(s):"})
        for filename in raw_file_texts:
            messages.append({"role": "user", "content": f"File: {filename}"})
            messages.append({"role": "user", "content": raw_file_texts[filename]})
            if grading_reports[filename] != "":
                messages.append({"role": "system", "content": "This is a syntax analysis of the file" + grading_reports[filename]})

        messages.append({"role": "user", "content": "This is the rubric :" + prompt})

        response = openai.ChatCompletion.create(
            messages=messages,
            engine=azure_openai_model,
            
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        logging.error("OpenAI API error: %s", str(e))
        return "Error in grading"

def authenticate_user(username, password):
    # Azure Cosmos DB configuration
    key = os.environ['COSMOS_DB_KEY']  # Cosmos DB primary key
    container_name = os.environ['COSMOS_DB_USER_CONTAINER']  # Container name

    try:
        # Create a Cosmos client
        client = CosmosClient.from_connection_string(os.environ['COSMOS_DB_CONNECTION_STRING'])

        # Select the database and container
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)

        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Query to authenticate the user
        query = "SELECT * FROM c WHERE c.userid=@username AND c.password=@password"
        parameters = [
            {"name": "@username", "value": username},
            {"name": "@password", "value": hashed_password}
        ]

        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        return len(items) > 0

    except CosmosHttpResponseError as e:
        logging.error("Cosmos DB error: %s", str(e))
        return False


st.set_page_config(page_title="Cengage Auto Grader", page_icon="cengage-favicon.png")

st.title("Cengage Auto Grader")

title_alignment="""
<style>
#cengage-auto-grader {
  text-align: center
}
</style>
"""

st.markdown(title_alignment, unsafe_allow_html=True)

# Hide the 'Made with Streamlit' footer
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 


user = st.text_input("Username")
password = st.text_input("Password", type="password")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if st.button("Login", use_container_width=True):
    st.session_state['authenticated'] = authenticate_user(user, password)
    if st.session_state['authenticated']:
        st.success("Logged in successfully")
    else:
        st.error("Invalid username or password")


if st.session_state['authenticated']:
    try:
        book_titles = ['', 'Minnick Responsive Web Design with HTML 5 and CSS, 9e', 'Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e']
    except Exception as e:
        logging.error("Database error: %s", str(e))
        st.error("Error loading data")
        book_titles = []

    if book_titles:
        # Select Book Title
        book_title = st.selectbox("Select Book Title", options=book_titles)
        st.session_state['selected_book'] = book_title

        if 'selected_book' in st.session_state and st.session_state['selected_book'] != '':

            # Select Chapter
            chapter = st.selectbox("Select Chapter", options=CHAPTER_DICT[st.session_state['selected_book']])
            st.session_state['selected_chapter'] = chapter

            if 'selected_chapter' in st.session_state and st.session_state['selected_chapter'] != '':

                # Select Exercise
                exercise = st.selectbox("Select Exercise", options=EXERCISE_DICT[st.session_state['selected_book']][st.session_state['selected_chapter']])
                st.session_state['selected_exercise'] = exercise

                if 'selected_exercise' in st.session_state and st.session_state['selected_exercise'] != '':
                    prompt = fetch_prompt(st.session_state['selected_book'], st.session_state['selected_chapter'], st.session_state['selected_exercise'])
                    if prompt:
                        st.write("Rubric: \n", prompt["prompt"])

                        # File Uploader
                        uploaded_file = st.file_uploader("Upload your answer file", type=["zip"])
                        if uploaded_file is not None:
                            with st.spinner('Grading in progress...'):
                                grade = grade_submission(uploaded_file, prompt["prompt"])
                            st.write("Suggestive Grading Report:\n", grade)
                    else:
                        st.error("Rubric not found for the selected exercise")
