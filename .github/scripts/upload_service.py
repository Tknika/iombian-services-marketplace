import sys
from typing import Any, Dict
import json
import os

import firebase_admin
import yaml
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

from parse_labels import parse_labels


def upload_to_services(
    upload: Dict[str, Any], service_name: str, service_version: str, db: Client
):
    service = db.collection("services").document(service_name)
    if not service.get().exists:
        _, service = db.collection("services").add({}, service_name)

    version = service.collection("versions").document(service_version)
    if version.get().exists:
        version.set(upload)
    else:
        service.collection("versions").add(upload, service_version)


if __name__ == "__main__":
    service_account_key = os.environ.get("SERVICE_ACCOUNT_KEY")
    if not service_account_key:
        exit(1)
    service_account_key = json.loads(service_account_key)

    cred = credentials.Certificate(service_account_key)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    path_to_docker_compose = sys.argv[1]
    service_name = path_to_docker_compose.split("/")[1]
    service_version = path_to_docker_compose.split("/")[2]

    with open(path_to_docker_compose, "r") as docker_compose_txt:
        docker_compose = yaml.safe_load(docker_compose_txt)

    labels = parse_labels(docker_compose, service_name)

    upload_to_services(
        {"labels": labels, "compose": docker_compose}, service_name, service_version, db
    )
