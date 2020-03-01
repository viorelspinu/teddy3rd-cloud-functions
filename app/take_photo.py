import time
import os
from google.cloud import storage
from PIL import Image



storage_client = storage.Client()

BUCKET_IN = "teddy-bucket-in"


def upload_to_bucket():
    bucket = storage_client.get_bucket(BUCKET_IN)
    blob = bucket.blob("in_photo.jpg")

    blob.upload_from_filename("snapshot.jpg")

    print("snapshot uploaded")


while(True):
    input("Press Enter to take photo.")
    os.system("imagesnap -w 2")
    upload_to_bucket()
    image = Image.open('snapshot.jpg')
    image.show()
    time.sleep(1)
