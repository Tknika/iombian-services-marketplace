import sys

from compose_validator import validate_compose
from error_message_parser import parse_error_message

class ComposeValidationError(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message

if __name__ == "__main__":
    path_to_docker_compose = sys.argv[1]

    service_name = path_to_docker_compose.split("/")[1]

    try:
        validate_compose(path_to_docker_compose, service_name)
    except Exception as e:
        error_message = parse_error_message(e)
        print(f"::error file={path_to_docker_compose}:: {error_message}")
        raise ComposeValidationError(f"{error_message}\nFile: {path_to_docker_compose}")
