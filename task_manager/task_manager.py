import glob
import logging
import os
import secrets
import shutil
import time
from datetime import datetime

import boto3
import pandas as pd
import s3fs
from cvat_sdk import make_client
from cvat_sdk.api_client import ApiClient, Configuration, exceptions
from cvat_sdk.api_client.models import InvitationWriteRequest, RegisterSerializerExRequest, RoleEnum
from cvat_sdk.core.proxies.tasks import ResourceType
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)


def dl_from_s3(pyro_bucket, src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    pyro_bucket.download_file(Key=src, Filename=dst)


def up_to_s3(pyro_bucket, src, dst):
    pyro_bucket.upload_file(Key=src, Filename=dst)


def dl_labels(aws_access_key_id, aws_secret_access_key):
    s3 = s3fs.S3FileSystem(anon=False, key=aws_access_key_id, secret=aws_secret_access_key)
    s3.invalidate_cache()
    labels = s3.glob("pyronear-data/done/labels/*.zip")
    os.makedirs("data/labels/", exist_ok=True)
    for label in labels:
        label = label.split("pyronear-data/")[1]
        local_file = "data/labels/" + os.path.basename(label)
        if not os.path.isfile(local_file):
            dl_from_s3(pyro_bucket, label, local_file)
            shutil.unpack_archive(local_file, local_file.split(".zip")[0], "zip")


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


def assign_task(host, credentials, username, password):
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        user = client.users.list()[0]  # take last user
        df = pd.read_csv("data/task_database.csv", index_col=0)
        df_free = df.loc[df["assign"].isnull()]
        task_id = int(df_free.iloc[0]["task_id"])
        df.loc[df["task_id"] == task_id, ["assign", "username", "password"]] = [user.id, username, password]
        df.to_csv("data/task_database.csv")
        task = client.tasks.retrieve(task_id)
        task.update({"assignee_id": user.id})


def assign_task_to_new_user():
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
            assign_task(configuration.host, (configuration.username, configuration.password), username, password)

            return (username, password)
        except exceptions.ApiException as e:
            err_msg = "Exception when calling AuthApi.create_register(): %s\n" % e
            return (err_msg, None)


def create_task(host, credentials, name, folder):
    # Create a Client instance bound to a local server and authenticate using basic auth
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        task_spec = {
            "name": name,
            "labels": [{"name": "smoke", "color": "#ff00ff", "attributes": []}],
        }

        imgs = glob.glob(folder + "/*.jpg")

        data_params = {}
        data_params["image_quality"] = 80

        task = client.tasks.create_from_data(
            spec=task_spec,
            data_params=data_params,
            resource_type=ResourceType.LOCAL,
            resources=[file for file in imgs],
        )

        task.fetch()

        return task


def register_task(task_name, task_id):
    if not os.path.isfile("data/task_database.csv"):
        df = pd.DataFrame(
            {
                "task_id": [task_id],
                "task_name": task_name,
                "assign": [None],
                "username": "username",
                "password": "password",
                "create_time": [datetime.now()],
                "assign_time": [None],
            }
        )

    else:
        df = pd.read_csv("data/task_database.csv", index_col=0)
        new_row = pd.DataFrame(
            {
                "task_id": [task_id],
                "task_name": task_name,
                "assign": [None],
                "username": "username",
                "password": "password",
                "create_time": [datetime.now()],
                "assign_time": [None],
            }
        )
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv("data/task_database.csv")


def add_new_task(task_name, pyro_bucket, host, credentials):
    # Get data
    logging.info(f"add task {task_name}")
    if task_name is not None:
        dl_from_s3(pyro_bucket, f"to-annotate/{task_name}.zip", f"data/aws/{task_name}.zip")
        shutil.unpack_archive(f"data/aws/{task_name}.zip", f"data/aws/{task_name}", "zip")
        # Create task

        task = create_task(host, credentials, task_name, f"data/aws/{task_name}")

        try:
            # Update labels
            os.makedirs("data/tasks", exist_ok=True)
            task.export_dataset(format_name="YOLO 1.1", filename=f"data/tasks/{task_name}.zip")
            shutil.unpack_archive(f"data/tasks/{task_name}.zip", f"data/tasks/{task_name}", "zip")
            labels = glob.glob(f"data/aws/{task_name}/labels/*.txt")
            for label_file in labels:
                new_label = os.path.join(task_name, "obj_train_data", os.path.basename(label_file))
                if os.path.isfile(new_label):
                    shutil.copy(label_file, new_label)
            os.remove(f"data/tasks/{task_name}.zip")
            shutil.make_archive(f"data/tasks/{task_name}", "zip", f"data/tasks/{task_name}")

            task.import_annotations(format_name="YOLO 1.1", filename=f"data/tasks/{task_name}.zip")
            register_task(task_name, task.id)

        except Exception:
            task.remove()
            logging.warning("Remove task if creation failed")
        # Clean
        if os.path.isfile(f"data/aws/{task_name}.zip"):
            os.remove(f"data/aws/{task_name}.zip")
        if os.path.isdir(f"data/aws/{task_name}"):
            shutil.rmtree(f"data/aws/{task_name}")
        if os.path.isdir(f"data/tasks/{task_name}"):
            shutil.rmtree(f"data/tasks/{task_name}")

        logging.info(f"{task_name} added")

        assign_task_to_new_user()  # create a user and assign it to the last created task
        logging.info(f"user created")


def get_task_list(host, credentials):
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        return client.tasks.list()


def process_task(pyro_bucket, task, save_to_s3=True, reload_task=True, reassign=True):
    # Get data
    task_name = task.name
    logging.info(f"Processing task: {task_name}")

    # Save
    if save_to_s3:
        os.makedirs("data/temp", exist_ok=True)
        if os.path.isfile(f"data/temp/{task_name}.zip"):
            os.remove(f"data/temp/{task_name}.zip")
        if os.path.isdir(f"data/temp/{task_name}"):
            shutil.rmtree(f"data/temp/{task_name}")
        task.export_dataset(format_name="YOLO 1.1", filename=f"data/temp/{task_name}.zip")
        shutil.unpack_archive(f"data/temp/{task_name}.zip", f"data/temp/{task_name}", "zip")
        if os.path.isfile(f"data/temp/{task_name}.zip"):
            os.remove(f"data/temp/{task_name}.zip")
        # Drop images
        imgs = glob.glob(f"data/temp/{task_name}/obj_train_data/*.jpg")
        [os.remove(file) for file in imgs]
        # Upload to S3
        shutil.make_archive(f"data/temp/{task_name}", "zip", f"data/temp/{task_name}")
        up_to_s3(pyro_bucket, f"done/labels/{task_name}_{datetime.now().isoformat()}.zip", f"data/temp/{task_name}.zip")
        if os.path.isfile(f"data/temp/{task_name}.zip"):
            os.remove(f"data/temp/{task_name}.zip")
        if os.path.isdir(f"data/temp/{task_name}"):
            shutil.rmtree(f"data/temp/{task_name}")

    if reload_task:
        task.import_annotations(format_name="YOLO 1.1", filename=f"data/tasks/{task_name}.zip")

    if reassign:
        df = pd.read_csv("data/task_database.csv", index_col=0)
        df.loc[df["task_name"] == task.name, ["assign", "username", "password", "assign_time"]] = [
            None,
            "username",
            "password",
            None,
        ]
        df.to_csv("data/task_database.csv")
        # Renew job
        job = task.get_jobs()[0]
        job.update({"state": "new"})
        job.update({"stage": "annotation"})
        # Assign new user
        assign_task_to_new_user()

    logging.info(f"completed task: {task_name} was processed")


if __name__ == "__main__":

    # Get data
    load_dotenv(".env")
    host = os.environ.get("HOST")
    username = os.environ.get("USERNAME")
    password = os.environ.get("PASSWORD")
    credentials = (username, password)
    aws_access_key_id = os.environ.get("AWS_KEY")
    aws_secret_access_key = os.environ.get("AWS_ACC")
    resource = boto3.resource("s3", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    pyro_bucket = resource.Bucket("pyronear-data")

    update_delta = 3

    while True:
        start_ts = time.time()

        try:
            dl_labels(aws_access_key_id, aws_secret_access_key)
        except Exception:
            logging.warning("Unable to dl labels")

        try:
            # Check available tasks
            s3 = s3fs.S3FileSystem(anon=False, key=aws_access_key_id, secret=aws_secret_access_key)
            s3.invalidate_cache()
            s3_tasks = s3.glob("pyronear-data/to-annotate/*.zip")

            # Add missing ones
            for task_file in s3_tasks:
                task_name = os.path.basename(task_file).split(".")[0]
                if not os.path.isfile(f"data/tasks/{task_name}.zip"):
                    add_new_task(task_name, pyro_bucket, host, credentials)

        except Exception:
            logging.warning("Unable to add new task")

        task_list = get_task_list(host, credentials)
        df = pd.read_csv("data/task_database.csv", index_col=0)
        df_assigned = df.loc[~df["assign_time"].isnull()]
        for task in task_list:
            if task.status == "completed":
                try:
                    process_task(pyro_bucket, task, save_to_s3=True, reload_task=True, reassign=True)
                except Exception:
                    logging.warning("Unable to process completed task")
            else:
                try:
                    if task.name in df_assigned["task_name"].values:
                        data = df_assigned[df_assigned["task_name"] == task.name]
                        if len(data) == 1:
                            assign_time = datetime.strptime(
                                data["assign_time"].values[0].split(".")[0], "%Y-%m-%d %H:%M:%S"
                            )
                            dt = datetime.now() - assign_time
                            if dt.days >= 1:
                                process_task(pyro_bucket, task, save_to_s3=False, reload_task=True, reassign=True)

                except Exception:
                    logging.warning("Unable to process olf task")
        time.sleep(max(update_delta - time.time() + start_ts, 1))
