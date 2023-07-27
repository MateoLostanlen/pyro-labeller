import glob
import logging
import os
import shutil
import time
from datetime import datetime

import boto3
import pandas as pd
from cvat_sdk import make_client
from cvat_sdk.core.proxies.tasks import ResourceType
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)


def dl_from_s3(pyro_bucket, src, dst):
    pyro_bucket.download_file(Key=src, Filename=dst)


def up_to_s3(pyro_bucket, src, dst):
    pyro_bucket.upload_file(Key=src, Filename=dst)


def dl_labels(aws_access_key_id, aws_secret_access_key):
    s3 = s3fs.S3FileSystem(anon=False,key=aws_access_key_id, secret=aws_secret_access_key)
    labels = s3.glob('pyronear-data/done/*.zip')
    os.makedirs("data/labels/", exist_ok=True)
    for label in labels:
        label = label.split('pyronear-data/')[1]
        local_file = "data/labels/" + os.path.basename(label)
        if not os.path.isfile(local_file):
            dl_from_s3(pyro_bucket, label, local_file)
            shutil.unpack_archive(local_file, local_file.split('.zip')[0], "zip")


def get_task(pyro_bucket):
    dl_from_s3(pyro_bucket, "dataset_status.csv", "dataset_status.csv")
    df = pd.read_csv("dataset_status.csv", index_col=0)
    if len(df[df["State"] == "TODO"]) == 0:
        df["State"] = ["TODO"] * len(df)
    for i in range(len(df)):
        data = df.iloc[i]
        if str(data["State"]) == "TODO":
            df.at[i, "State"] = "ONGOING"
            df.to_csv("dataset_status.csv")
            up_to_s3(pyro_bucket, "dataset_status.csv", "dataset_status.csv")
            os.remove("dataset_status.csv")
            return str(data["Name"])


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


def get_task_list(host, credentials):
    with make_client(host=host, credentials=credentials) as client:
        client.organization_slug = "Pyronear"
        return client.tasks.list()


def register_task(task_name, task_id):
    if not os.path.isfile("data/task_database.csv"):
        df = pd.DataFrame(
            {
                "task_id": [task_id],
                "task_name": task_name,
                "assign": [None],
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
                "create_time": [datetime.now()],
                "assign_time": [None],
            }
        )
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv("data/task_database.csv")


def add_new_task(pyro_bucket, host, credentials):
    # Get data
    task_name = get_task(pyro_bucket)
    logging.info(f"add task {task_name}")
    if task_name is not None:
        dl_from_s3(pyro_bucket, f"to-annotate/{task_name}.zip", f"{task_name}.zip")
        shutil.unpack_archive(f"{task_name}.zip", f"{task_name}_aws", "zip")
        # Create task
        time.sleep(0.5)

        task = create_task(host, credentials, task_name, f"{task_name}_aws")
        register_task(task_name, task.id)

        try:
            os.remove(f"{task_name}.zip")
            # Update labels
            time.sleep(0.5)
            task.export_dataset(format_name="YOLO 1.1", filename=f"{task_name}.zip")
            shutil.unpack_archive(f"{task_name}.zip", f"{task_name}", "zip")
            labels = glob.glob(f"{task_name}_aws/labels/*.txt")
            for label_file in labels:
                new_label = os.path.join(task_name, "obj_train_data", os.path.basename(label_file))
                if os.path.isfile(new_label):
                    shutil.copy(label_file, new_label)
            os.remove(f"{task_name}.zip")
            shutil.make_archive(task_name, "zip", task_name)
            time.sleep(0.5)
            task.import_annotations(format_name="YOLO 1.1", filename=f"{task_name}.zip")
            # register_task(task_name, task.id)

        except Exception:
            task.remove()
            logging.warning("Remove task if creation failed")
        # Clean
        if os.path.isfile(f"{task_name}.zip"):
            os.remove(f"{task_name}.zip")
        if os.path.isfile(task_name):
            shutil.rmtree(task_name)
        if os.path.isfile(f"{task_name}_aws"):
            shutil.rmtree(f"{task_name}_aws")

        logging.info(f"{task_name} added")


def mark_task_done(pyro_bucket, task_name):
    dl_from_s3(pyro_bucket, "dataset_status.csv", "dataset_status.csv")
    df = pd.read_csv("dataset_status.csv", index_col=0)
    df.loc[df["Name"] == task_name, "State"] = "DONE"
    df.to_csv("dataset_status.csv")
    up_to_s3(pyro_bucket, "dataset_status.csv", "dataset_status.csv")
    os.remove("dataset_status.csv")
    logging.info(f"{task_name} completed")


def del_task(task_id):
    df = pd.read_csv("data/task_database.csv", index_col=0)
    df = df[df.task_id != task_id]
    df.to_csv("data/task_database.csv")


def process_completed_task(pyro_bucket, task):
    # Get data
    del_task(task.id)
    task_name = task.name
    logging.info(f"Process completed task: {task_name}")
    task.export_dataset(format_name="YOLO 1.1", filename=f"{task_name}.zip")
    shutil.unpack_archive(f"{task_name}.zip", f"{task_name}", "zip")
    # Drop images
    imgs = glob.glob(f"{task_name}/obj_train_data/*.jpg")
    [os.remove(file) for file in imgs]
    # Upload to S3
    shutil.make_archive(task_name, "zip", task_name)
    up_to_s3(pyro_bucket, f"done/{task_name}_{datetime.now().isoformat()}.zip", f"{task_name}.zip")
    # Clean
    mark_task_done(pyro_bucket, task_name)
    os.remove(f"{task_name}.zip")
    shutil.rmtree(task_name)
    task.remove()
    logging.info(f"completed task: {task_name} was processed")


def reassign_old_task():
    if os.path.isfile("data/task_database.csv"):
        df = pd.read_csv("data/task_database.csv", index_col=0)
        df_assigned = df.loc[~df["assign"].isnull()]
        for i in range(len(df_assigned)):
            data = df[df["task_id"] == df_assigned.iloc[i]["task_id"]]
            idx = data.index[0]
            assign_time = data["assign_time"]
            if assign_time is not None:
                assign_time = datetime.strptime(assign_time.values[0].split(".")[0], "%Y-%m-%d %H:%M:%S")
                dt = datetime.now() - assign_time
                if dt.days >= 1:
                    df.at[idx, "assign"] = None
                    df.at[idx, "assign_time"] = None

        df.to_csv("data/task_database.csv")


def drop_removed_task(task_list):
    task_list_id = [task.id for task in task_list]
    if os.path.isfile("data/task_database.csv"):
        df = pd.read_csv("data/task_database.csv", index_col=0)
        to_drop = []
        for i in range(len(df)):
            data = df.iloc[i]
            if data["task_id"] not in task_list_id:
                to_drop.append(i)

        df = df.drop(index=to_drop)
        df.to_csv("data/task_database.csv")


if __name__ == "__main__":

    load_dotenv(".env")
    host = os.environ.get("HOST")
    username = os.environ.get("USERNAME")
    password = os.environ.get("PASSWORD")
    credentials = (username, password)
    aws_access_key_id = os.environ.get("AWS_KEY")
    aws_secret_access_key = os.environ.get("AWS_ACC")
    resource = boto3.resource("s3", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    pyro_bucket = resource.Bucket("pyronear-data")

    update_delta = 30

    while True:
        start_ts = time.time()
        task_list = get_task_list(host, credentials)
        drop_removed_task(task_list)
        reassign_old_task()
        dl_labels(aws_access_key_id, aws_secret_access_key)

        try:
            if sum([task.assignee is None for task in task_list]) < 10:
                add_new_task(pyro_bucket, host, credentials)
        except Exception:
            logging.warning("Unable to add new task")

        for task in task_list:
            if task.status == "completed":
                try:
                    process_completed_task(pyro_bucket, task)
                except Exception:
                    logging.warning("Unable to process completed task")
            else:
                try:
                    if len(task.get_frames_info()) == 0:
                        task.remove()
                except Exception:
                    logging.warning("Unable to remove empty task")
        time.sleep(max(update_delta - time.time() + start_ts, 1))
