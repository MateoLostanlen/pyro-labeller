import glob
import logging
import os
import shutil

import boto3
import pandas as pd
from boto3.session import Session
from cvat_sdk import make_client
from cvat_sdk.core.proxies.tasks import ResourceType
from dotenv import load_dotenv


def dl_from_s3(session, bucket, src, dst):
    session.resource("s3").Bucket(bucket).download_file(Key=src, Filename=dst)


def up_to_s3(session, bucket, src, dst):
    session.resource("s3").Bucket(bucket).upload_file(Key=src, Filename=dst)


def get_task(session):
    dl_from_s3(session, bucket, "dataset_status.csv", "dataset_status.csv")
    df = pd.read_csv("dataset_status.csv", index_col=0)
    for i in range(len(df)):
        data = df.iloc[i]
        if str(data["State"]) == "TODO":
            df.at[i, "State"] = "ONGOING"
            df.to_csv("dataset_status.csv")
            up_to_s3(session, bucket, "dataset_status.csv", "dataset_status.csv")
            return str(data["Name"])


def create_task(host, credentials, name, folder):
    # Create a Client instance bound to a local server and authenticate using basic auth
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        task_spec = {
            "name": name,
            "labels": [{"name": "smoke", "color": "#ff00ff", "attributes": []}],
        }

        imgs = glob.glob(folder + "/*.jpg")[:5]

        data_params = {}
        data_params["image_quality"] = 80

        client.tasks.create_from_data(
            spec=task_spec,
            data_params=data_params,
            resource_type=ResourceType.LOCAL,
            resources=[file for file in imgs],
        )


def get_task_list(host, credentials):
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        return client.tasks.list()


def add_new_task(session, host, credentials):
    # Get data
    task_name = get_task(session)
    if task_name is not None:
        dl_from_s3(session, bucket, f"to-annotate/{task_name}.zip", f"{task_name}.zip")
        shutil.unpack_archive(f"{task_name}.zip", f"{task_name}_aws", "zip")
        # Create task
        create_task(host, credentials, task_name, f"{task_name}_aws")
        os.remove(f"{task_name}.zip")
        # Update labels
        task_list = get_task_list(host, credentials)[:5]
        task = task_list[0]
        task.export_dataset(format_name="YOLO 1.1", filename=f"{task_name}.zip")
        shutil.unpack_archive(f"{task_name}.zip", f"{task_name}", "zip")
        labels = glob.glob(f"{task_name}_aws/labels/*.txt")
        for label_file in labels:
            new_label = os.path.join(task_name, "obj_train_data", os.path.basename(label_file))
            if os.path.isfile(new_label):
                shutil.copy(label_file, new_label)
        os.remove(f"{task_name}.zip")
        shutil.make_archive(task_name, "zip", task_name)
        task.import_annotations(format_name="YOLO 1.1", filename=f"{task_name}.zip")
        # Clean
        os.remove(f"{task_name}.zip")
        shutil.rmtree(task_name)
        shutil.rmtree(f"{task_name}_aws")


def process_completed_task(session, task):
    # Get data
    task_name = task.name
    task.export_dataset(format_name="YOLO 1.1", filename=f"{task_name}.zip")
    shutil.unpack_archive(f"{task_name}.zip", f"{task_name}", "zip")
    # Drop images
    imgs = glob.glob(f"{task_name}/obj_train_data/*.jpg")
    [os.remove(file) for file in imgs]
    # Upload to S3
    shutil.make_archive(task_name, "zip", task_name)
    up_to_s3(session, bucket, f"done/{task_name}.zip", f"{task_name}.zip")
    # Clean
    os.remove(f"{task_name}.zip")
    shutil.rmtree(task_name)
    task.remove()


if __name__ == "__main__":
    s3 = boto3.resource("s3")
session = Session()
bucket = "pyronear-data"
load_dotenv(".env")
host = os.environ.get("HOST")
username = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")
credentials = (username, password)

update_delta = 30

while True:
    start_ts = time.time()
    task_list = get_task_list(host, credentials)
    for task in task_list:
        if task.status == "completed":
            try:
                process_completed_task(session, task)
            except Exception:
                logging.warning("Unable to process completed task")

    task_list = get_task_list(host, credentials)
    try:
        if sum([task.assignee is None for task in task_list]) < 10:
            add_new_task(session, host, credentials)
    except Exception:
        logging.warning("Unable to add new task")
    time.sleep(max(update_delta - time.time() + start_ts, 0))
