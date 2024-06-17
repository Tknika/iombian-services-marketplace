from pydantic import ValidationError
from python_on_whales import DockerException


def parse_error_message(exception: Exception):
    if isinstance(exception, DockerException):
        error = exception.stderr
        print(error)
        if not error:
            return "Something went wrong while validating the docker compose structure."

        lines = error.split("\n")
        error_message = lines[-2]

        return f"Error in docker compose structure:\n{error_message}"

    elif isinstance(exception, ValidationError):
        error_messages = [message["msg"] for message in exception.errors()]
        if len(error_messages) == 1:
            error_message = error_messages[0]
        else:
            error_count = exception.error_count()
            error_message = f"{error_count} errors found while validating the service\n{'\n'.join(error_messages)}"

        return error_message
    else:
        print(type(exception))
        return "An unexpected error occurred while validating the service"
