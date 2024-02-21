import subprocess

def run_eslint(file_path):
    try:
        result = subprocess.run(['jshint', '--config', '.jshintrc', file_path], capture_output=True, text=True)
        return result.stdout if result.stdout else result.stderr
    except subprocess.CalledProcessError as e:
        return str(e)