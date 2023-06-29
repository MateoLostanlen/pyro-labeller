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


def get_task(pyro_bucket):
    dl_from_s3(pyro_bucket, "dataset_status.csv", "dataset_status.csv")
    df = pd.read_csv("dataset_status.csv", index_col=0)
    if len(df[df["State"]=="TODO"])==0:
        df["State"] = ["TODO"]*len(df)
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

def register_task(task_name, task_id):
    if not os.path.isfile("data/task_database.csv"):
        df = pd.DataFrame({'task_id':[task_id], 'task_name':task_name, 'assign':[None], 'create_time': [datetime.now()], 'assign_time': [None]})
        
    else:
        df = pd.read_csv("data/task_database.csv", index_col=0)
        new_row = pd.DataFrame({'task_id':[task_id], 'task_name':task_name, 'assign':[None], 'create_time': [datetime.now()], 'assign_time': [None]})
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv("data/task_database.csv")


def add_new_task(pyro_bucket, host, credentials, task_id):
    # Get data
    task_name = get_task(pyro_bucket)
    logging.info(f"add task {task_name}")
    if task_name is not None:
        dl_from_s3(pyro_bucket, f"to-annotate/{task_name}.zip", f"{task_name}.zip")
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
        register_task(task_name, task_id)
        # Clean
        os.remove(f"{task_name}.zip")
        shutil.rmtree(task_name)
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


def process_completed_task(pyro_bucket, task):
    # Get data
    del_task(task.id)
    task_name = task.name
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

    # Clean
    # Delete all task
    task_list = get_task_list(host, credentials)
    [task.remove() for task in task_list] 
    if os.path.isfile("data/task_database.csv"):
        os.remove("data/task_database.csv")

    update_delta = 30

    while True:
        start_ts = time.time()
        task_list = get_task_list(host, credentials)
        try:
            if sum([task.assignee is None for task in task_list]) < 10:
                if len(task_list)>0:
                    task_id = task_list[0].id + 1
                else:
                    task_id = 1
                add_new_task(pyro_bucket, host, credentials, task_id)
        except Exception:
            logging.warning("Unable to add new task")
          
        for task in task_list:
            if task.status == "completed":
                try:
                    process_completed_task(pyro_bucket, task)
                except Exception:
                    logging.warning("Unable to process completed task")
        time.sleep(max(update_delta - time.time() + start_ts, 0))
