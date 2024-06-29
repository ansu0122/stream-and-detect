# Traffic detection and tracking project with kafka streams

Stream Producer service splits the video file aka. stream into frames and publishes it to Kafka "Detect" topic with N partitions.

Detector service subscribes to "Detect" topic, receives messages with the frames, decodes them and detects the traffic object using YOLOv8n model. The model is trained on the traffic object like as follows: 'bicycle', 'bus', 'car', 'motorbike', 'person'.
The detection results are persisted into output folder of the S3 bucket or the project directory. 
Detector published the detection results to Tracker topic.

Tracker services subscribes to Track topic and uses DeepSort algorithm along with YOLOv8n model to track and count the unique traffic object over time. The outcomes of the tracking are logged to the csv file and recorder in the video.


> docker-compose -f docker-compose-local.yaml up --build -d

> docker-compose -f docker-compose-local.yaml down

remove cache
> docker builder prune