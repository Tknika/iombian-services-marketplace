from typing import Dict, TypedDict

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


def parse_labels(docker_compose: dict, service_name: str) -> Dict[str, ParsedLabels]:
    """Given the docker-compose in dict/json form, return the label information."""
    services = docker_compose["services"]
    parsed_labels = {}
    env_order = 0

    for service in services:
        service_labels = {}
        labels = services[service].get("labels") or {}

        for label, value in labels.items():
            splitted_label = label.split(".")
            namespace = splitted_label[0]
            label_service_name = splitted_label[1]
            label_type = splitted_label[2]

            if namespace != "com" or label_service_name != service:
                continue

            if label_type == "service" and label_service_name == service_name:
                service_metadata_key = splitted_label[3]
                parsed_labels[service_metadata_key] = value

            elif label_type == "env":
                if not service_labels.get("envs"):
                    service_labels["envs"] = {}
                env_name = splitted_label[3]

                if not service_labels["envs"].get(env_name):
                    service_labels["envs"][env_name] = {}
                    service_labels["envs"][env_name]["order"] = str(env_order)
                    env_order += 1

                env_metadata_key = splitted_label[4]
                service_labels["envs"][env_name][env_metadata_key] = value

        parsed_labels[service] = service_labels

    return parsed_labels
