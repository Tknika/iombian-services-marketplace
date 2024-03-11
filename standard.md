# IoMBian Marketplace Standard

### 0.1.0

This is the standard to follow when uploading services to the IoMBian Services Marketplace. 

To add a new service, create a folder with the name of the service inside the "services" folder of the "iombian-services-marketplace" repository.
The folder name can only contain alphanumeric characters and the words that compose it must be separated by hyphens ("-"), never by blank spaces.
As will be seen later, this name must be the same as the name of the service and the name of the container that will be defined in the docker-compose.yml file.
Finally, the different versions of the service must be stored in separate folders, identifying the version number in the folder name.

Example:

```
services/iombian-button-handler/0.1.0/docker-compose.yml
services/iombian-button-handler/0.1.1/docker-compose.yml
services/iombian-button-handler/0.2.0/docker-compose.yml
services/iombian-shutdown-handler/0.1.0/docker-compose.yml
services/iombian-config-file-handler/0.1.0/docker-compose.yml
```

All the information about the service should be stored in the docker-compose.yml file and it should be able to be executed with a simple "docker compose up", without having to execute any other command.

First you will need to define the name of the service, the name of the container that will be generated and the image.
The name of the service and the name of the container must be the same and it must be composed of alphanumeric characters and the words must be separated by the hyphen symbol ("-"), blanks are not allowed.
The image will need to be external, it can’t have a build argument.
The image can be stored in Docker Hub, GitHub Container Registry or any other alternative.

It is recommended that the service doesn't have privileges if it doesn't need them.
Unless the service is launched by some other event, the restart parameter will be "unless-stopped", not "always".
This way the service can be started automatically when starting the machine.

Here is a fragment of the iombian-button-handler service as an example:

```
services:
    iombian-button-handler:
        image: ghcr.io/tknika/iombian-button-handler:sha-0bfb0d5
        container_name: iombian-button-handler
        privileged: true
        restart: unless-stopped
```

## Volumes
Define the volumes as you would in a normal docker compose file.
Here is an example of the iombian-config-file-handler:

```
volumes:
    - /boot/config/parameters.yml:/app/parameters.yml
```

## Networks

The user created services will go in the iombian-external-services network.
This network is already created in the IoMBian operating system.
To use the iombian-external-services this has to be added to the docker compose file:

Inside of the service:

```
networks:
    - iombian-external-services
```

And outside of the service:

```
networks:
    iombian-external-services:
        external: true
```

## Ports

Define the ports as you would in a normal docker compose file, but make the mapped port value definable through an environment value.
Here is an example of the iombain-button-handler:

```
ports:
    - ${BUTTON_EVENTS_PORT:-5556}:5556
```

## Environments

Define the environment variables as you would in a normal docker compose file.
The environments defined in this section will be the ones that are passed to the container, not the ones that the user can change from the IoMBian configurator user interface.
Here is an example of the iombian-button-handler:

```
environment:
    BUTTON_PIN: ${BUTTON_PIN:-3}
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
```

## Labels

The label names will be structured with dots.
All labels will start with `com.<service-name>`.
This `<service-name>` must be the same as the main service name and the container name.
After that, the type of the label will be defined: service or env (environment variables).
Then the structure will vary depending on the type.

### Service

This will define metadata or information about the service. The labels will start with `com.<service-name>.service`.
- name: The name of the service in a more readable way. Without the hyphens.
- author: The author of the service.
- version: The version of the service.
The structure of the version will be: `major.minor.patch-pre-release-label`.
The pre-release-label is optional.
The version of the compose file and the version of the image don’t need to be the same.
- description: A short description of the service.
- changelog: A short description of what has changed from the previous version.

Here is an example of the iombian-button-handler service:

```
com.iombian-button-handler.service.name: "IoMBian button handler"
com.iombian-button-handler.service.author: "Aitor Castaño"
com.iombian-button-handler.service.version: "0.1.0"
com.iombian-button-handler.service.description: "Raspberry GPIO button handler. Publishes the registered button event using ZeroMQ as the communication protocol."
```

### Environment variables

The environment variables will have some metadata in order to know what those variables are or mean.
The environment variables here are the ones for the docker compose file, defined with ${}, not for the environment variables passed to the container, defined in the compose file.
The environment variables defined with ${} and referenced in the labels are the ones that the user will be able to change from the user interface of the IoMBian configurator.
There will be a group of labels for each environment variable.
The labels will start with `com.<service-name>.env.<variable-name>`.

- name: The name of the variable in a more readable way.
Without being all in uppercase, without underscores and all that.
- description: A short description of the variable: what it is, what it is for…
- type: The type of the variable value. The type can be:
    - "integer"
        - You can specify extra information after the type using ":".
        You can specify the min and max values that the integer can have separated with ";".
        Here is an example:
        - `"integer:0;100"`
    - "string"
        - Here you can also specify extra information with ":".
        First you can specify if the string is going to be hidden like a password or not when shown in the iombian-configurator ui. 0 shows the string and 1 shows it.
        After that, separated with ";" you can specify a regex the string should follow.
        You can leave it empty if no regex is needed.
        - `"string:0;"`
    - "float"
        - Here is similar to the integer.
        With ":" you define the information and separate with ";".
        You can also define min and max.
        - `"float:10.5;20.5"`
    - "boolean"
        - The boolean type doesn't have any extra information.
    - "enum"
        - The enum has the type before the ":" and the possibilities after separated with ",".
        The options are defined without spaces between the commas.
        - `"enum:NOTSET,DEBUG,INFO,WARNING,WARN,ERROR,FATAL,CRITICAL"`
- default: The default value of the variable

Here is an example of the labels of the environment variables of the iombian-button-handler:

```
com.iombian-button-handler.env.BUTTON_EVENTS_PORT.name: "Button events port"
com.iombian-button-handler.env.BUTTON_EVENTS_PORT.description: "Port for communicating button events."
com.iombian-button-handler.env.BUTTON_EVENTS_PORT.type: "integer"
com.iombian-button-handler.env.BUTTON_EVENTS_PORT.default: 5556

com.iombian-button-handler.env.BUTTON_PIN.name: "Button pin"
com.iombian-button-handler.env.BUTTON_PIN.description: "The pin of the raspberry button."
com.iombian-button-handler.env.BUTTON_PIN.type: "integer"
com.iombian-button-handler.env.BUTTON_PIN.default: 3

com.iombian-button-handler.env.LOG_LEVEL.name: "Log level"
com.iombian-button-handler.env.LOG_LEVEL.description: "Log level for the python logger (INFO, DEBUG, ...)."
com.iombian-button-handler.env.LOG_LEVEL.type: "string"
com.iombian-button-handler.env.LOG_LEVEL.default: "INFO"
```

## Final example

```
services:
    iombian-example-service:
        image: ghcr.io/example/image
        container_name: iombian-example-service
        restart: unless-stopped
        volumes:
            - <external_path>:<internal_path>
        networks:
            - iombian-external-services
        ports:
            - ${PORT_ENV:-5555}:5555
        environment:
            EXAMPLE_ENV: ${EXAMPLE_ENV:-default}
        labels:
            com.iombian-example-service.service.name: "IoMian example service" 
            com.iombian-example-service.service.author: "<author_name>"
            com.iombian-example-service.service.version: "0.1.0"
            com.iombian-example-service.service.description: "Example functionality of the example service"

            com.iombian-example-service.env.PORT_ENV.name: "Port env"
            com.iombian-example-service.env.BUTTON_EVENTS_PORT.description: "Example functionality of Port env."
            com.iombian-example-service.env.BUTTON_EVENTS_PORT.type: "integer"
            com.iombian-example-service.env.BUTTON_EVENTS_PORT.default: 5555

            com.iombian-example-service.env.EXAMPLE_ENV.name: "Example env"
            com.iombian-example-service.env.EXAMPLE_ENV.description: "Example functionality of example env"
            com.iombian-example-service.env.EXAMPLE_ENV.type: "string"
            com.iombian-example-service.env.EXAMPLE_ENV.default: "default"

networks:
    iombian-external-services:
        external: true
```
