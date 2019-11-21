# code adapted from https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/functions/ocr

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import os

from google.cloud import pubsub_v1
from google.cloud import storage
from google.cloud import translate
from google.cloud import vision
from google.cloud import texttospeech
from flask import send_file

vision_client = vision.ImageAnnotatorClient()
translate_client = translate.Client()
publisher = pubsub_v1.PublisherClient()
storage_client = storage.Client()
text_to_speech_client = texttospeech.TextToSpeechClient()

project_id = os.environ['GCP_PROJECT']

MP3_READY_TOPIC = "mp3-ready-topic"
LABELS_TOPIC = "labels-topic"
TRANSLATED_TEXT_TOPIC = "translated-text-topic"
MP3_OUT_BUCKET = "teddy-bucket-out"
CONFIGURATION_BUCKET = "teddy-settings"
CONFIGURATION_FILE = "teddy-settings.json"
TRANSLATE_TO_LANG = ["en", "fr"]


def process_image(file, context):
    """Cloud Function triggered by Cloud Storage when a file is changed.
    Args:
        file (dict): Metadata of the changed file, provided by the triggering
                                 Cloud Storage event.
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to stdout and Stackdriver Logging
    """
    bucket = validate_message(file, 'bucket')
    name = validate_message(file, 'name')

    detect_labels(bucket, name)

    print('File {} processed.'.format(file['name']))


def detect_labels(bucket, filename):
    print('Running cloud vision on {}'.format(filename))

    futures = []

    text_detection_response = vision_client.label_detection({
        'source': {'image_uri': 'gs://{}/{}'.format(bucket, filename)}
    })

    annotations = text_detection_response.label_annotations
    if len(annotations) > 0:
        text = ""
        for a in annotations:
            text = text + a.description + ", "
    else:
        text = 'did not see anything, sorry'
    print('Extracted labels {} from image.'.format(text))

    src_lang = 'en'

    # Submit a message to the LABELS_TOPIC topic for each target language
    for target_lang in TRANSLATE_TO_LANG:
        topic_name = LABELS_TOPIC
        message = {
            'text': text,
            'filename': filename,
            'lang': target_lang,
            'src_lang': src_lang
        }
        message_data = json.dumps(message).encode('utf-8')
        topic_path = publisher.topic_path(project_id, topic_name)
        future = publisher.publish(topic_path, data=message_data)
        futures.append(future)
    for future in futures:
        future.result()


def translate_text(event, context):

    print("enter translate_text")

    if event.get('data'):
        message_data = base64.b64decode(event['data']).decode('utf-8')
        message = json.loads(message_data)
    else:
        raise ValueError('Data sector is missing in the Pub/Sub message.')

    text = validate_message(message, 'text')
    filename = validate_message(message, 'filename')
    target_lang = validate_message(message, 'lang')
    src_lang = validate_message(message, 'src_lang')

    print('Translating text into {} from {}.'.format(target_lang, src_lang))
    final_text = ""
    if (target_lang == src_lang):
        final_text = text
    else:
        translated_text = translate_client.translate(text,
                                                     target_language=target_lang,
                                                     source_language=src_lang)
        final_text = translated_text['translatedText']

    topic_name = TRANSLATED_TEXT_TOPIC
    message = {
        'text': final_text,
        'filename': filename,
        'lang': target_lang,
    }

    message_data = json.dumps(message).encode('utf-8')
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, data=message_data)
    future.result()


def text_to_speech(event, context):
    if event.get('data'):
        message_data = base64.b64decode(event['data']).decode('utf-8')
        message = json.loads(message_data)
    else:
        raise ValueError('Data sector is missing in the Pub/Sub message.')

    text = validate_message(message, 'text')
    filename = validate_message(message, 'filename')
    filename_no_extension = filename.rsplit(".", 1)[0]
    lang = validate_message(message, 'lang')

    print('Received translated text {}.'.format(text))

    synthesis_input = texttospeech.types.SynthesisInput(text=text)

    speech_lang = "en-US"
    if (lang == "fr"):
        speech_lang = "fr-FR"

    voice = texttospeech.types.VoiceSelectionParams(
        language_code=speech_lang,
        ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    response = text_to_speech_client.synthesize_speech(synthesis_input, voice, audio_config)

    print("Generated MP3 from text {} using {} language.".format(text, speech_lang))

    bucket_name = MP3_OUT_BUCKET
    result_filename = '{}_{}.mp3'.format(filename.rsplit(".", 1)[0], lang)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(result_filename)

    print('Saving MP# to {} in bucket {}.'.format(result_filename, bucket_name))
    blob.upload_from_string(response.audio_content)

    topic_name = MP3_READY_TOPIC
    message = {
        'original_filename': filename,
        'lang': lang,
        'bucket': MP3_OUT_BUCKET,
        'mp3_filename': filename_no_extension + "_" + lang + ".mp3"
    }

    message_data = json.dumps(message).encode('utf-8')
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, data=message_data)
    future.result()
    print("Published MP3 ready message to topic {}".format(topic_path))


def retrieve_configuration(request):
    bucket = storage_client.get_bucket(CONFIGURATION_BUCKET)
    blob = bucket.blob(CONFIGURATION_FILE)

    configuration_json = blob.download_as_string().decode("utf-8")
    print(configuration_json)
    return configuration_json


def update_configuration(request):

    # TODO:get params from request and write to configuration json in Google Bucket Storage
    return "OK"

# [START message_validatation_helper]


def validate_message(message, param):
    var = message.get(param)
    if not var:
        raise ValueError('{} is not provided. Make sure you have \
                          property {} in the request'.format(param, param))
    return var
# [END message_validatation_helper]
