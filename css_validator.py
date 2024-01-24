import cssutils
import logging

cssutils.log.setLevel(logging.CRITICAL)  # To suppress non-critical logs

def validate_css(file_path):
    with open(file_path, 'r') as file:
        css_content = file.read()

    parser = cssutils.CSSParser(raiseExceptions=True)
    try:
        parser.parseString(css_content)
        return "CSS is valid"
    except Exception as e:
        return f"CSS validation error: {e}"
