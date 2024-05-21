import re
from typing import Any, Dict, List, Literal, TypeAlias, TypeVar

import yaml
from pydantic import BaseModel, field_validator, model_validator
from python_on_whales import DockerClient

T = TypeVar("T")

Networks: TypeAlias = Dict[
    Literal["iombian-internal-services", "iombian-external-services"],
    Dict[Literal["external"], bool],
]


def env_has_labels(env_var: str, labels: Dict[str, str], service: str):
    """Given a environment variable, checks if it has its respective labels."""
    env_info = ["name", "description", "type", "default"]
    for info in env_info:
        label_key = f"com.{service}.env.{env_var}.{info}"
        if labels.get(label_key) is None:
            return False
    return True


def get_vars_from_string(string: str):
    """Get all the environment variables defined in the given string.

    The environment variables are the names inside of `${}`, for example:
    ```
    >>> get_vars_from_string("${BUTTON_EVENTS_PORT}")
    ["BUTTON_EVENTS_PORT"]
    ```

    """
    env_vars = re.findall(r"\$\{([^\}]+)\}", string)
    env_vars = [str(env_var) for env_var in env_vars]
    return env_vars


class Service(BaseModel):
    """Model defining the structure of a service in a docker compose."""

    image: str
    container_name: str
    privileged: bool | None = False
    restart: Literal["unless-stopped", "no", "on-failure"]
    networks: List[Literal["iombian-internal-services", "iombian-external-services"]]
    ports: List[str] | None = None
    volumes: List[str] | None = None
    environment: Dict[str, Any] | None = None
    labels: Dict[str, str] | None = None

    @field_validator("labels")
    @classmethod
    def label_starts_with_com(cls, labels: Dict[str, str]):
        """Check if all the labels in the service start with "com"."""
        for label in labels:
            namespace = label.split(".")[0]
            if namespace != "com":
                raise ValueError('label must start with "com"')
        return labels

    @field_validator("labels")
    @classmethod
    def label_type(cls, labels: Dict[str, str]):
        """Check if label type is "service" or "env"."""
        for label in labels:
            label_type = label.split(".")[2]
            if label_type != "service" and label_type != "env":
                raise ValueError('label type must be "service" or "env"')
        return labels

    @field_validator("labels")
    @classmethod
    def type_validation(cls, labels: Dict[str, str]):
        """For each label group, check if the type is correct and the default value follows the given type.

        Example:
        --------
            ```
            com.<service>.env.<env_var>.type: "integer:10;"
            com.<service>.env.<env_var>.default: "20"
            ```
            Gives an error because type definition is wrong.

            ```
            com.<service>.env.<env_var>.type: "integer:10;50"
            com.<service>.env.<env_var>.default: "5"
            ```
            Gives an error because the default value doesn't follow the given type (min and max).

            ```
            com.<service>.env.<env_var>.type: "integer:10;50"
            com.<service>.env.<env_var>.default: "20"
            ```
        """
        for label in labels:
            splitted_label = label.split(".")
            service = splitted_label[1]
            label_type = splitted_label[2]

            if label_type == "env":
                env_name = splitted_label[3]
                env_info = splitted_label[4]

                if env_info == "type":
                    type_value = labels[label]
                    default_key = f"com.{service}.env.{env_name}.default"
                    default_value = labels[default_key]
                    env_type = type_value.split(":")[0]

                    if env_type not in [
                        "integer",
                        "float",
                        "string",
                        "boolean",
                        "enum",
                    ]:
                        raise ValueError("invalid variable type")

                    if len(type_value.split(":")) == 1:
                        if env_type == "integer":
                            int(default_value)
                        elif env_type == "float":
                            float(default_value)
                        elif env_type == "boolean":
                            if default_value != "true" and default_value != "false":
                                raise ValueError('boolea must be "true" or "false"')

                    if len(type_value.split(":")) == 2:
                        if env_type == "integer":
                            min_max = type_value.split(":")[1]
                            min = int(min_max.split(";")[0])
                            max = int(min_max.split(";")[1])

                            default_value = int(default_value)
                            if not min <= default_value <= max:
                                raise ValueError(
                                    "default integer value must be in the given range"
                                )

                        elif env_type == "float":
                            min_max = type_value.split(":")[1]
                            min = float(min_max.split(";")[0])
                            max = float(min_max.split(";")[1])

                            default_value = float(default_value)
                            if not min <= default_value <= max:
                                raise ValueError(
                                    "default integer value must be in the given range"
                                )

                        elif env_type == "string":
                            hidden = type_value[6:9]
                            regex = type_value[:9]

                            if hidden != ":0;" and hidden != ":1;":
                                raise ValueError("invalid string type definition")

                            if re.fullmatch(regex, default_value) is None:
                                raise ValueError(
                                    "defualt string value must match the given regex"
                                )

                        elif env_type == "enum":
                            enum_values = type_value.split(":")[1]
                            enum_values = enum_values.split(",")
                            if default_value not in enum_values:
                                raise ValueError(
                                    "default enum value must be part of the enum"
                                )

        return labels

    @model_validator(mode="after")
    def container_name_is_in_labels(self):
        """Check if the container name is the same as the service name in the labels."""
        if not self.labels:
            return self

        for label in self.labels:
            label_service = label.split(".")[1]
            if label_service != self.container_name:
                raise ValueError(
                    "container_name and label service name must be the same"
                )
        return self

    @model_validator(mode="after")
    def env_has_label(self):
        """For each environment variable defined with `${}`, check if it has the necessary labels.

        The necessary labels are:
            - name
            - description
            - type
            - default
        """
        all_vars: List[str] = []
        if self.ports:
            for port in self.ports:
                port_vars = get_vars_from_string(port)
                all_vars += port_vars

        if self.volumes:
            for volume in self.volumes:
                volume_vars = get_vars_from_string(volume)
                all_vars += volume_vars

        if self.environment:
            for env in self.environment:
                env_vars = get_vars_from_string(env)
                all_vars += env_vars

                env_value = str(self.environment[env])
                env_value_vars = get_vars_from_string(env_value)
                all_vars += env_value_vars

        for var in all_vars:
            if not self.labels or not env_has_labels(var, self.labels, self.container_name):
                raise ValueError(f"environment variable {var} has no labels")

        return self


Services: TypeAlias = Dict[str, Service]


class DockerCompose(BaseModel):
    services: Services
    networks: Networks
    service_name: str

    @field_validator("networks")
    @classmethod
    def external_network(cls, values: Networks):
        """Check if the network used by the service is external."""
        networks = list(values.keys())

        if len(networks) != 1:
            raise ValueError("Can only have one network")
        network = networks.pop()

        external = values[network]["external"]
        if not external:
            raise ValueError("The network must be external")

        return values

    @field_validator("services")
    @classmethod
    def same_service_container_name(cls, services: Services):
        """For each service, check if the service and the container_name are the same."""
        for service in services:
            container_name = services[service].container_name
            if container_name != service:
                raise ValueError("service name and container name msut be the same.")
        return services

    @model_validator(mode="after")
    def main_service_has_data(self):
        """Check that there is a main service and that the main service has the services metadata.

        The main service is docker service which has the same name as the parent service.
        """
        services_with_service_name = [
            service for service in self.services if service == self.service_name
        ]
        if len(services_with_service_name) != 1:
            raise ValueError(
                "service must contain one docker service with the same name"
            )

        main_service = self.services[services_with_service_name[0]]
        service_info = [
            "name",
            "author",
            "version",
            "description",
            "changelog",
            "documentation_url",
        ]
        for info in service_info:
            label_key = f"com.{self.service_name}.service.{info}"
            if not main_service.labels or main_service.labels.get(label_key) is None:
                raise ValueError(f"main service labels must contain {info}")
        return self


def validate_compose(path_to_compose: str, service_name: str):
    """Validate the compose given the path to the compose and the name of the main service.

    The name of the main service is the name of the folder inside the services.

    For example in: `services/iombian-button-handler/0.1.0/docker-compose.yaml` the service name is `iombian-button-handler`.
    """
    docker = DockerClient(compose_files=[path_to_compose])
    docker.compose.config()

    with open(path_to_compose, "r") as docker_compose_txt:
        docker_compose = yaml.safe_load(docker_compose_txt)

    validated_compose = DockerCompose(**docker_compose, service_name=service_name)

    return validated_compose
