import time

from google.cloud import pubsub_v1

project_id = "ocr-demo-259005"
subscription_name = "gcf-ocr-save-ocr_result_topic"

subscriber = pubsub_v1.SubscriberClient()

subscription_path = subscriber.subscription_path(    project_id, subscription_name)

def callback(message):
    print('Received message: {}'.format(message))
    message.ack()

subscriber.subscribe(subscription_path, callback=callback)

# The subscriber is non-blocking. We must keep the main thread from
# exiting to allow it to process messages asynchronously in the background.
print('Listening for messages on {}'.format(subscription_path))
while True:
    time.sleep(60)