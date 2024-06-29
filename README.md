# Traffic detection and tracking project with kafka streams

Stream Producer service splits the video file aka. stream into frames and publishes it to Kafka "Detect" topic with N partitions.

Detector service subscribes to "Traffic" topic, receives messages with the frames, decodes them and detects the traffic object using YOLOv8n model. The model is trained on the traffic object like as follows: 'bicycle', 'bus', 'car', 'motorbike', 'person'. The detection results are persisted into output folder of the S3 bucket or the project directory _output/detect/_ 

Tracker services subscribes to "Traffic" topic and uses YOLOv8 Tracking algorithm to track and count the unique traffic object (cars and motorbikes) crossing the boundary line. The outcomes of the tracking are logged to the json file and recorder as the video file written to _output/track_ folder

* Command to spin the services with local setup
> docker-compose -f docker-compose-local.yaml up --build -d --scale detector=3
* Command to shut down the services with local setup
> docker-compose -f docker-compose-local.yaml down

* Command to spin the services with s3 setup
> export AWS_ACCESS_KEY_ID = access_key_id_here
> export AWS_SECRET_ACCESS_KEY = secret_access_key_here
> docker-compose -f docker-compose-s3.yaml up --build -d --scale detector=3
* Command to shut down the services with s3 setup
> docker-compose -f docker-compose-s3.yaml down