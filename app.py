import streamlit as st
import openai
import pandas as pd
import hashlib
import os
import logging
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
            return None, None

    except CosmosHttpResponseError as e:
        logging.error("Cosmos DB error: %s", str(e))
        return None, None

def grade_submission(file, prompt):
    try:
        grading_reports, raw_file_texts = syntax_check(file)

        messages=[{"role": "system", "content": "You are an auto grader for web programing courses. You will be given the student codes and rubric as well as extra information if anay. Fill out the rubric and provide justification for your grading. Never add up the total grade or do any math."}]
        
        messages.append({"role": "system", "content": "You are grading the following file(s):"})
        for filename in raw_file_texts:
            messages.append({"role": "user", "content": f"File: {filename}"})
            messages.append({"role": "user", "content": raw_file_texts[filename]})
            grading_report = grading_reports[filename]["messages"][0] if len(grading_reports[filename]["messages"]) > 0 else None
            if grading_report:
                messages.append({"role": "system", "content": "This is a syntax analysis of the file" + grading_report})

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



st.title("Cengage Auto Grader")

title_alignment="""
<style>
#cengage-auto-grader {
  text-align: center
}
</style>
"""

st.markdown(title_alignment, unsafe_allow_html=True)

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
            chapters = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

            # Select Chapter
            chapter = st.selectbox("Select Chapter", options=chapters)
            st.session_state['selected_chapter'] = chapter

            if 'selected_chapter' in st.session_state and st.session_state['selected_chapter'] != '':
                exercises = ['', 'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'ex7', 'ex8', 'ex9', 'ex10']

                # Select Exercise
                exercise = st.selectbox("Select Exercise", options=exercises)
                st.session_state['selected_exercise'] = exercise

                if 'selected_exercise' in st.session_state and st.session_state['selected_exercise'] != '':
                    prompt = fetch_prompt(st.session_state['selected_book'], st.session_state['selected_chapter'], st.session_state['selected_exercise'])
                    if prompt:
                        st.write("Rubric: ", prompt["prompt"])

                        # File Uploader
                        uploaded_file = st.file_uploader("Upload your answer file", type=["zip"])
                        if uploaded_file is not None:
                            grade = grade_submission(uploaded_file, prompt["prompt"])
                            st.write("Suggestive Grading Report:\n", grade)
