pip install -r ./requirements.txt

gcloud config set project teddy-serverless 
gsutil mb gs://teddy-bucket-in    
gsutil mb gs://teddy-bucket-out
gcloud pubsub topics create labels-topic
gcloud pubsub topics create translated-text-topic
gcloud pubsub topics create mp3-ready-topic      
gcloud pubsub subscriptions create mp3-ready-subscriptions --topic mp3-ready-topic
gcloud functions deploy process_image --runtime python37 --trigger-bucket teddy-bucket-in --entry-point process_image
gsutil cp ../sign.png gs://teddy-bucket-in
gcloud functions logs read --limit 100
gcloud functions deploy translate_text --runtime python37 --trigger-topic labels-topic --entry-point translate_text
gsutil cp ../sign.png gs://teddy-bucket-in
gcloud functions logs read --limit 100
gcloud functions deploy text-to-speech --runtime python37 --trigger-topic translated-text-topic --entry-point text_to_speech
gsutil cp ../sign.png gs://teddy-bucket-in
gcloud functions logs read --limit 100
export GOOGLE_APPLICATION_CREDENTIALS=/Users/viorels/Downloads/teddy-serverless-60abe4f631db.json
