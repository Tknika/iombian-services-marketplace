import sys

from compose_validator import validate_compose

if __name__ == "__main__":
    path_to_docker_compose = sys.argv[1]

    service_name = path_to_docker_compose.split("/")[1]

    try:
        validate_compose(path_to_docker_compose, service_name)
    except Exception as e:
        error_message = str(e).split("\n")[2]
        print(f"::error file={path_to_docker_compose}:: {error_message}")
        raise e
