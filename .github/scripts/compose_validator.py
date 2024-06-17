import enum
import re
from typing import Any, Dict, List, Literal, TypeAlias, TypeVar

import yaml
from pydantic import BaseModel, field_validator, model_validator
from python_on_whales import DockerClient
from typing_extensions import IntVar

T = TypeVar("T")

Networks: TypeAlias = Dict[
    Literal["iombian-internal-services", "iombian-external-services"],
    Dict[Literal["external"], bool],
]

VALID_TYPES = ["integer", "float", "string", "boolean", "enum"]


def get_missing_label(env_var: str, labels: Dict[str, str], service: str):
    """Get the missing label of the given environment variable.

    If the variable has a missing label, the name of that label will be returned.
    In another case, return an empty string"""
    env_info = ["name", "description", "type", "default"]
    for info in env_info:
        label_key = f"com.{service}.env.{env_var}.{info}"
        if labels.get(label_key) is None:
            return info
    return ""


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
                raise ValueError(f'label "{label}" must start with "com"')
        return labels

    @field_validator("labels")
    @classmethod
    def label_type(cls, labels: Dict[str, str]):
        """Check if label type is "service" or "env"."""
        for label in labels:
            label_type = label.split(".")[2]
            if label_type != "service" and label_type != "env":
                raise ValueError(f'label "{label}" type must be "service" or "env"')
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

                    if ":" not in type_value:
                        env_type = type_value
                        env_constraint = None
                    else:
                        env_type, env_constraint = type_value.split(":", 1)

                    if env_type not in VALID_TYPES:
                        raise ValueError(
                            f"invalid environment variable type: {env_type}.\nEnvironment variable type must be {', '.join(VALID_TYPES[:-1])} or {VALID_TYPES[-1]}."
                        )

                    # if ":" not in type_value:
                    #     if env_type == "integer":
                    #         int(default_value)
                    #     elif env_type == "float":
                    #         float(default_value)
                    #     elif env_type == "boolean":
                    #         if default_value != "true" and default_value != "false":
                    #             raise ValueError(
                    #                 f'boolean "{default_value}" must be "true" or "false"'
                    #             )

                    if env_type == "integer":

                        try:
                            default_value = int(default_value)
                        except ValueError:
                            raise ValueError(
                                f'default value "{default_value}" must be an integer'
                            )

                        if env_constraint is not None:
                            if ";" not in env_constraint:
                                raise ValueError(
                                    f'min and max must be separated by a semicolon ";": {env_constraint}'
                                )

                            [min, max] = env_constraint.split(";", 1)

                            try:
                                min = int(min)
                            except ValueError:
                                raise ValueError(f"min must be an integer: {min}")

                            try:
                                max = int(max)
                            except ValueError:
                                raise ValueError(f"max must be an integer: {max}")

                            if not min <= default_value <= max:
                                raise ValueError(
                                    f'default value "{default_value}" must be in the given range: [{min}, {max}]'
                                )

                    elif env_type == "float":
                        try:
                            default_value = float(default_value)
                        except ValueError:
                            raise ValueError(
                                f'default value "{default_value}" must be a float'
                            )

                        if env_constraint is not None:
                            if ";" not in env_constraint:
                                raise ValueError(
                                    f'min and max must be separated by a semicolon ";": {env_constraint}'
                                )

                            [min, max] = env_constraint.split(";", 1)

                            try:
                                min = float(min)
                            except ValueError:
                                raise ValueError(f"min must be a float: {min}")

                            try:
                                max = float(max)
                            except ValueError:
                                raise ValueError(f"max must be a float: {max}")

                            if not min <= default_value <= max:
                                raise ValueError(
                                    f'default value "{default_value}" must be in the given range: [{min}, {max}]'
                                )

                    elif env_type == "string":
                        if env_constraint is not None:
                            hidden = env_constraint[:2]
                            regex = env_constraint[2:]
                            regex = ".*" if regex == "" else regex

                            if hidden != "0;" and hidden != "1;":
                                raise ValueError(
                                    f'invalid string type definition: "{type_value}"\nShow (0;) or hidden (1;) must be defined'
                                )

                            if re.fullmatch(regex, default_value) is None:
                                raise ValueError(
                                    f'default string "{default_value}" must match the given regex: {regex}'
                                )

                    elif env_type == "enum":
                        if not env_constraint:
                            raise ValueError(
                                f'enum must have at least one option: "{type_value}"'
                            )

                        enum_values = env_constraint.split(",")
                        if default_value not in enum_values:
                            raise ValueError(
                                f'default enum value "{default_value}" must be part of the enum: {enum_values}'
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
                    f'container_name "{self.container_name}" and label service "{label_service}" name must be the same'
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
            if not self.labels:
                raise ValueError(f"service has no labels")

            missing_label = get_missing_label(var, self.labels, self.container_name)
            if missing_label != "":
                raise ValueError(
                    f'environment variable "{var}" has no label "{missing_label}"'
                )

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
            raise ValueError("service can only have one network")
        network = networks.pop()

        external = values[network]["external"]
        if not external:
            raise ValueError("the network must be external")

        return values

    @field_validator("services")
    @classmethod
    def same_service_container_name(cls, services: Services):
        """For each service, check if the service and the container_name are the same."""
        for service in services:
            container_name = services[service].container_name
            if container_name != service:
                raise ValueError(
                    f'service name "{service}" and container name "{container_name}" must be the same'
                )
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
                f'service "{self.service_name}" must contain one docker service with the same name'
            )

        main_service = self.services[services_with_service_name[0]]
        service_info = [
            "id",
            "name",
            "author",
            "version",
            "description",
            "changelog",
            "documentation_url",
        ]
        for info in service_info:
            label_key = f"com.{self.service_name}.service.{info}"
            if not main_service.labels:
                raise ValueError("main service must have the service labels labels")

            if main_service.labels.get(label_key) is None:
                raise ValueError(f'main service labels must contain "{info}"')

            if info == "id" and main_service.labels.get(label_key) != self.service_name:
                raise ValueError(
                    f'the id of the service "{self.service_name}" must be the same as the main service name "{main_service.labels.get(label_key)}"'
                )
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
