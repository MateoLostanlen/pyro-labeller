import os
import secrets

from cvat_sdk import make_client
from cvat_sdk.api_client import ApiClient, Configuration, exceptions
from cvat_sdk.api_client.models import InvitationWriteRequest, RegisterSerializerExRequest, RoleEnum
from dotenv import load_dotenv
import logging
import time
import pandas as pd
from datetime import datetime

def gen_password():
    password = secrets.token_urlsafe(12).replace("-", "").replace("_", "")
    return password[:10]


def get_configuration():

    load_dotenv(".env")
    return Configuration(
        host=os.environ.get("HOST"),
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
    )


def get_new_user_idx(configuration):
    with ApiClient(configuration) as api_client:
        return int(api_client.users_api.list()[0]["results"][0]["id"]) + 1


def add_to_organization(configuration, email):
    with ApiClient(configuration) as api_client:
        invitation_write_request = InvitationWriteRequest(
            role=RoleEnum("worker"),
            email=email,
        )
        try:
            (data, response) = api_client.invitations_api.create(
                invitation_write_request,
                org="Pyronear",
            )
        except exceptions.ApiException as e:
            print("Exception when calling InvitationsApi.create(): %s\n" % e)


def assign_task(host, credentials):
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        user = client.users.list()[0]  # take last user
        df = pd.read_csv("data/task_database.csv", index_col=0)
        df_free = df.loc[df['assign'].isnull()]
        task_id = int(df_free.iloc[0]["task_id"])
        df.loc[df['task_id'] == task_id,["assign", "assign_time"]]=[user.id, datetime.now()]
        df.to_csv("data/task_database.csv")
        task = client.tasks.retrieve(task_id)
        task.update({"assignee_id": user.id})


def create_user():
    configuration = get_configuration()
    user_idx = get_new_user_idx(configuration)
    username = f"pyro_user_{str(user_idx).zfill(9)}"
    email = f"{username}@pyronear.org"
    password = gen_password()
    with ApiClient(configuration) as api_client:
        register_serializer_ex_request = RegisterSerializerExRequest(
            username=username,
            email=email,
            password1=password,
            password2=password,
            first_name=username,
            last_name="Pyronear",
        )

        try:
            (data, response) = api_client.auth_api.create_register(
                register_serializer_ex_request,
            )
            add_to_organization(configuration, email)
            assign_task(configuration.host, (configuration.username, configuration.password))
        
            return (username, password)
        except exceptions.ApiException as e:
            err_msg = "Exception when calling AuthApi.create_register(): %s\n" % e
            return (err_msg, None)
