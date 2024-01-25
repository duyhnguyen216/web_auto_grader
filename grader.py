import zipfile
import os
from html_validator import validate_html_w3c
from eslint_runner import run_eslint
from css_validator import validate_css
import shutil
import tempfile

def process_zip(file):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def syntax_check(file):
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
                eslint_result = run_eslint(file_path)
                grading_report[filename] = eslint_result
            elif filename.endswith('.html'):
                html_validation_result = validate_html_w3c(file_path)
                html_validation_feedback = ""
                for message in html_validation_result['messages']:
                    if message['type'] == 'error':
                        html_validation_feedback += f"Error: {message['message']} at line {message['lastLine']}\n"
                grading_report[filename] = html_validation_feedback
            elif filename.endswith('.css'):
                css_validation_result = validate_css(file_path)
                grading_report[filename] = css_validation_result

    # Clean up extracted files
    shutil.rmtree(temp_dir)

    return grading_report, raw_file_text
