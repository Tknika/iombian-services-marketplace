from typing import Dict, TypedDict

import yaml

Env = TypedDict(
    "Env",
    {"name": str, "description": str, "type": str, "default": str | int | float | bool},
)


class ParsedLabels(TypedDict):
    name: str
    author: str
    version: str
    description: str
    changelog: str
    documentation_url: str
    envs: Dict[str, Env]


def parse_labels(docker_compose: dict) -> Dict[str, ParsedLabels]:
    """Given the docker-compose in dict/json form, return the label information."""
    services = docker_compose["services"]
    parsed_labels = {}

    for service in list(services.keys()):
        service_labels = {}
        labels = services[service]["labels"]

        for label in list(labels.keys()):
            value = labels[label]

            splitted_label = label.split(".")
            namespace = splitted_label[0]
            service_name = splitted_label[1]
            label_type = splitted_label[2]

            if namespace != "com" or service_name != service:
                continue

            if label_type == "service":
                service_metadata_key = splitted_label[3]
                service_labels[service_metadata_key] = value

            elif label_type == "env":
                if not service_labels.get("envs"):
                    service_labels["envs"] = {}
                env_name = splitted_label[3]

                if not service_labels["envs"].get(env_name):
                    service_labels["envs"][env_name] = {}

                env_metadata_key = splitted_label[4]
                service_labels["envs"][env_name][env_metadata_key] = value

        parsed_labels[service] = service_labels
    return parsed_labels


if __name__ == "__main__":
    with open("docker-compose.yaml", "r") as docker_compose_txt:
        docker_compose = yaml.safe_load(docker_compose_txt)

    labels = parse_labels(docker_compose)
    print(labels)
