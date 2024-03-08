import random
import streamlit as st
import openai
import pandas as pd
import hashlib
import os
import time
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.cosmos import CosmosClient, PartitionKey
import logging
from dotenv import load_dotenv
from grader import syntax_check

# Securely load environment variables
load_dotenv()
url = os.environ['COSMOS_DB_URL']  # Cosmos DB URL
database_name = os.environ['COSMOS_DB_DATABASE']  # Database name

def randomize_openai_api_settings():
    """Randomize the OpenAI API key."""
    settings = [
        {
            "api_key": "AZURE_OPENAI_API_KEY",
            "model": "AZURE_OPENAI_MODEL",
            "endpoint": "AZURE_OPENAI_ENDPOINT"
        },
        {
            "api_key": "AZURE_OPENAI_API_KEY_UK",
            "model": "AZURE_OPENAI_MODEL_UK",
            "endpoint": "AZURE_OPENAI_ENDPOINT_UK"
        }
    ]
    return random.choice(settings)

openai_settings = randomize_openai_api_settings()
azure_openai_api_key = os.environ.get(openai_settings["api_key"])
azure_openai_model = os.environ.get(openai_settings["model"])
azure_openai_endpoint = os.environ.get(openai_settings["endpoint"])

openai.api_version = "2023-05-15"
openai.api_type = "azure"
openai.api_key = azure_openai_api_key
openai.api_base = azure_openai_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """
You are an auto grader for web programing courses. You will be given the student codes, compilation results and rubric as well as extra information if any.
Do not be strict on comment and syntax style. For example if the task is to add the student name and date as a comment, accept any commenting style
and any name and dates that are not placeholders. Example of placeholder that should not be accepted are 'first name last name', 'MM/DD/YYYY', 'your name', 'today's date'
Example of acceptable name and date 'John Sminth', 'Hsung Tsai', '2/2/2000'. Remember, you can not verify the actual date and name or uploading task, so accept anything that is not an obvious placeholder;
Acceot tasks that you do not have the tools to verify and note that you were not able to actually verify it.
Fill out the rubric and provide justification for your grading. Refer to the line number with error when possible. Always show the achieved score in bold number. Never add up the total grade or do any math.
Provide these extra information afterward when aplicable, like compile error, tips to manually grade this submission for instructor, feedback for student.\n
Example:
1. {First rubric item} [Possible Score:{First possible score}] .\n- **Score: 1/1** {Justification and reasoning}\n\n
2. {Second rubric item} [Possible Score:{Second possible score}]\n- **Score: 2/3** {Justification and reasoning}\n\n
3. {Third rubric item} [Possible Score:{Third possilbe score}]\n- **Score: 3/3** {Justification and reasoning}\n\n
Addtional information: {Compile error}\n {Manual grading tips for instructor}\n {feedback for student}\n
"""

CHAPTER_DICT = {
    "Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e": ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    "Minnick Responsive Web Design with HTML 5 and CSS, 9e": ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    "Carey New Perspectives on HTML5, CSS3, and JavaScript 6e": ["", "11", "12", "13", "14"]
    }

EXERCISE_DICT = {
    "Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e": {
        "1":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "2":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "3":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "4":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "5":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "6":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "7":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "8":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "9":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"],
        "10":["", "cp01", "cp02", "ex01", "ex02", "ex03", "ex04", "rw01"]},
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
        "12":["", "analyze_correct_improve", "apply_your_knowledge", "extend_your_knowledge", "ex01", "ex02", "ex03", "yt01", "yt02", "yt03"]},

    "Carey New Perspectives on HTML5, CSS3, and JavaScript 6e": {
        "11":["", "cp01", "cp02", "cp03", "cp04", "rw01"],
        "12":["", "cp01", "cp02", "cp03", "cp04", "rw01"],
        "13":["", "cp01", "cp02", "cp03", "cp04", "rw01"],
        "14":["", "cp01", "cp02", "cp03", "cp04", "rw01"]}
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
        grading_reports, raw_file_texts = syntax_check(file, azure_openai_model)

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
        return "Error in grading (%s)" % str(e)
    
def grade_submission_stream(file, prompt):
    try:
        grading_reports, raw_file_texts = syntax_check(file, azure_openai_model)

        messages=[{"role": "system", "content": SYSTEM_PROMPT}]
        
        messages.append({"role": "user", "content": "You are grading the following file(s):"})
        for filename in raw_file_texts:
            messages.append({"role": "user", "content": f"File: {filename}"})
            messages.append({"role": "user", "content": raw_file_texts[filename]})
            if grading_reports[filename] != "":
                messages.append({"role": "system", "content": "This is a syntax analysis of the file" + grading_reports[filename]})

        messages.append({"role": "user", "content": "This is the rubric :" + prompt})

        stream = openai.ChatCompletion.create(
            messages=messages,
            engine=azure_openai_model,
            stream=True
        )
        return stream
    except Exception as e:
        logging.error("OpenAI API error: %s", str(e))
        return "Error in grading (%s)" % str(e)

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

st.markdown(
    """
    <style>
    @keyframes blink {
      0% { opacity: 0; }
      50% { opacity: 1; }
      100% { opacity: 0; }
    }

    .cursor-blink {
      display: inline-block;
      width: 2px;
      height: 1em;
      background: black; /* Visible on light backgrounds */
      animation: blink 1s step-end infinite;
    }

    @media (prefers-color-scheme: dark) {
      .cursor-blink {
        background: white; /* Visible on dark backgrounds */
      }
    }
    </style>
    """,
    unsafe_allow_html=True
)

cursor_blink_str = '<span class="cursor-blink"></span>'

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

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'report_placeholders' not in st.session_state:
    st.session_state['report_placeholders'] = {}
if 'reports' not in st.session_state:
    st.session_state['reports'] = {}
if 'is_grading' not in st.session_state:
    st.session_state['is_grading'] = False

if st.button("Login", use_container_width=True):
    st.session_state['authenticated'] = authenticate_user(user, password)
    if st.session_state['authenticated']:
        st.success("Logged in successfully")
    else:
        st.error("Invalid username or password")


if st.session_state['authenticated']:
    try:
        book_titles = ['', 'Minnick Responsive Web Design with HTML 5 and CSS, 9e', 'Carey New Perspectives on HTML 5 and CSS: Comprehensive 8e', 'Carey New Perspectives on HTML5, CSS3, and JavaScript 6e']
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

                def handle_grading(uploaded_file, prompt):
                    """Perform grading and update the placeholder with the report and download button."""
                    if uploaded_file.name not in st.session_state['report_placeholders']:
                        st.session_state['report_placeholders'][uploaded_file.name] = st.empty()
                    
                    placeholder = st.session_state['report_placeholders'][uploaded_file.name]
                    print(f"Grading {uploaded_file.name}...")
                    grade_report = ""
                    stream = grade_submission_stream(uploaded_file, prompt)
                    for chunk in stream:
                        if isinstance(stream, str) and "Error in grading" in stream:
                            st.error(stream)
                            break       
                        elif "content" in chunk.choices[0].delta:
                            grade_report += chunk.choices[0].delta.content
                            # Update the placeholder with the latest part of the grading report
                            with placeholder.container():
                                st.markdown(f"### Suggested grading for {uploaded_file.name}\n{grade_report}{cursor_blink_str}", unsafe_allow_html=True)
                    # Store the final report in session state
                    st.session_state['reports'][uploaded_file.name] = grade_report

                    # Update the placeholder with the final report and download button
                    with placeholder.container():
                        st.write(f"### Suggested grading for {uploaded_file.name}\n{grade_report}")

                        
                # Display prompt based on the selected exercise
                if 'selected_exercise' in st.session_state and st.session_state['selected_exercise'] != '':
                    promptResponse = fetch_prompt(st.session_state['selected_book'], st.session_state['selected_chapter'], st.session_state['selected_exercise'])

                    if promptResponse:
                        prompt = promptResponse["prompt"]
                        st.write("# Rubric: \n\n", prompt)

                        uploaded_files = st.file_uploader("Upload your answer file", accept_multiple_files=True, type=["zip"], key="file_uploader")

                        # Update session state with newly uploaded files
                        if uploaded_files:
                            st.session_state['uploaded_files'] = uploaded_files

                        result_container = st.container()

                        # Button to trigger grading
                        if st.button('Grade Submissions') or st.session_state['is_grading']:
                            st.session_state['is_grading'] = True
                            st.session_state['reports'] = {}
                            result_container.empty()
                            for uploaded_file in st.session_state['uploaded_files']:
                                    if st.session_state['report_placeholders'].get(uploaded_file.name) is not None:
                                        st.session_state['report_placeholders'][uploaded_file.name].empty()
                                    handle_grading(uploaded_file, prompt)
                            st.session_state['is_grading'] = False

                        #Clear the placeholders
                        for file_name in st.session_state['uploaded_files']:
                            if file_name.name in st.session_state['report_placeholders']:
                                with st.session_state['report_placeholders'][file_name.name].container():
                                    st.write("")

                        
                        # Reconstruct the view based on the persisted state
                        for uploaded_file in st.session_state['uploaded_files']:
                            file_name = uploaded_file.name
                            if file_name in st.session_state['reports']:
                                result_container.markdown(f"### Suggested grading for {file_name}")
                                result_container.write(st.session_state['reports'][file_name])
                                result_container.download_button(
                                    label=f"Download Report for {file_name}",
                                    data=st.session_state['reports'][file_name],
                                    file_name=f"{file_name}_grading_report.txt",
                                    mime="text/plain",
                                    key=file_name+"_final"
                                )
                    else:
                        st.error("Rubric not found for the selected exercise")