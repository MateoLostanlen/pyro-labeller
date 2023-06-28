import secrets

from cvat_sdk.api_client import ApiClient, Configuration, exceptions
from cvat_sdk.api_client.models import InvitationWriteRequest, RegisterSerializerExRequest, RoleEnum
from utils import get_ip
import os
from dotenv import load_dotenv




def gen_password():
    password = secrets.token_urlsafe(12).replace("-", "").replace("_", "")
    return password[:10]


def get_configuration():

    load_dotenv(".env")

    return Configuration(
        host=os.environ.get("HOST"),
        username=os.environ.get("USER"),
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


def create_user(email):
    print("dd")
    configuration = get_configuration()

   
    
    user_idx = get_new_user_idx(configuration)
    username = f"pyro_user_{str(user_idx).zfill(9)}"
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
            return (username, password)
        except exceptions.ApiException as e:
            err_msg = "Exception when calling AuthApi.create_register(): %s\n" % e
            return (err_msg, None)
