import time
import os
from google.cloud import storage

storage_client = storage.Client()

BUCKET_IN = "teddy-bucket-in"


def upload_to_bucket():
    bucket = storage_client.get_bucket(BUCKET_IN)
    blob = bucket.blob("in_photo.jpg")

    blob.upload_from_filename("snapshot.jpg")

    print("snapshot uploaded")


while(True):
    raw_input("Press Enter to take photo.")
    os.system("imagesnap -w 0.1")
    upload_to_bucket()
    time.sleep(1)
