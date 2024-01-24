import requests

def validate_html_w3c(file_path):
    url = 'https://validator.w3.org/nu/?out=json'
    headers = {'Content-Type': 'text/html; charset=utf-8'}

    with open(file_path, 'rb') as file:
        response = requests.post(url, headers=headers, data=file)

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error in validation: {response.status_code}"
