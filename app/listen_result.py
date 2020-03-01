import time
import json
import base64
import os

from google.cloud import pubsub_v1
from google.cloud import storage

storage_client = storage.Client()

project_id = "teddy-serverless"
subscription_name = "mp3-ready-subscriptions"

subscriber = pubsub_v1.SubscriberClient()

subscription_path = subscriber.subscription_path(project_id, subscription_name)


def callback(message):
    payload = json.loads(message.data.decode('utf-8'))
    print(payload)

    mp3_file = payload['mp3_filename']
    bucket_name = payload['bucket']
    print(mp3_file)

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(mp3_file)

    destination_file_name = mp3_file
    blob.download_to_filename(destination_file_name)

    message.ack()

    os.system("afplay " + destination_file_name)


subscriber.subscribe(subscription_path, callback=callback)
print('Listening for messages on {}'.format(subscription_path))

while True:
    time.sleep(60)
