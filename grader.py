import zipfile
import os
from html_validator import validate_html_w3c
from eslint_runner import run_eslint
from css_validator import validate_css
import shutil
import tempfile
import openai

JS_PROMPT = """you are a javascript syntax evaluator/compiler, output only the error messages and the code that cause the error. Ignore any warning or 
logical problem. In other words only output an error if there are syntax error. Assume that the javascript will be run by the browser, accept
all browser globals. Do not provide suggestion to improve the code. Format your output like a compiler, but refer to the code snippet instead of
line number and only return that output"""
def process_zip(file):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def syntax_check(file, azure_openai_model):
    temp_dir = process_zip(file)

    grading_report = {}
    raw_file_text = {}

    for dirpath, dirnames, filenames in os.walk(temp_dir):
        for filename in filenames:
            if filename.startswith('.') or (not filename.endswith('.js') and not filename.endswith('.css') and not filename.endswith('.html')):
                continue

            file_path = os.path.join(dirpath, filename)
            with open(file_path, 'r') as file:
                raw_file_text[filename] = file.read()

            if filename.endswith('.js'):
                # eslint_result = run_eslint(file_path)
                messages = [{'role':'system', 'content':JS_PROMPT}]
                messages.append({'role':'user', 'content':raw_file_text[filename]})
                eslint_result = openai.ChatCompletion.create(
                    messages=messages,
                    engine=azure_openai_model, 
                )['choices'][0]['message']['content']
                grading_report[filename] = eslint_result
            elif filename.endswith('.html'):
                html_validation_result = validate_html_w3c(file_path)
                html_validation_feedback = ""
                for message in html_validation_result['messages']:
                    if message['type'] == 'error' and 'lastLine' in message:
                        html_validation_feedback += f"Error: {message['message']} at line {message['lastLine']}\n"
                grading_report[filename] = html_validation_feedback
            elif filename.endswith('.css'):
                css_validation_result = validate_css(file_path)
                grading_report[filename] = css_validation_result

    # Clean up extracted files
    shutil.rmtree(temp_dir)

    return grading_report, raw_file_text
