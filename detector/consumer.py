import json
import math
import argparse
import os
import sys
import uuid
import signal
import numpy as np
from datetime import datetime
from confluent_kafka import DeserializingConsumer, Producer, KafkaError, KafkaException
from confluent_kafka.serialization import StringSerializer, StringDeserializer
import cv2
from ultralytics import YOLO


broker = 'broker:9092'
classNames = ['bicycle', 'bus', 'car', 'motorbike', 'person']

class MessageObj(object):
    def __init__(self, timestamp, frame_data):
        self.timestamp = timestamp
        self.frame_data = frame_data


class MessageObjDecoder:
    def __call__(self, value, ctx):
        data = json.loads(value.decode("utf-8"))
        return MessageObj(timestamp=datetime.fromisoformat(data['timestamp']),
                          frame_data=data['frame_data'])

class MessageObjectOut(object):
    def __init__(self, timestamp, frame_data, detections):
        self.timestamp = timestamp
        self.frame_data = frame_data
        self.detections = detections

class MessageObjEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, MessageObjectOut):
            return {
                'timestamp': obj.timestamp,
                'frame_data': obj.frame_data,
                'detections': obj.detections
            }
        else:
            return super().default(obj)
    
def signal_handler(sig, frame):
    print("Received SIGTERM, shutting down gracefully...")
    sys.exit(0)


def delivery_callback(err, msg):
    if err is not None:
        print("Delivery failed to {} topic at {} for {} with {} offset: {}".format(
            msg.topic(), msg.partition(), msg.key(), msg.offset(), err))
        return


class DetectorService:
   
    def __init__(self, broker, topic_in, topic_out, output_dir, model_path):

        config = {
            'bootstrap.servers': broker,
            'group.id': 'detector-group',
            'auto.offset.reset': 'earliest',
            'fetch.message.max.bytes': 20971520,
            'max.partition.fetch.bytes': 20971520
        }
        config['key.deserializer'] = StringDeserializer() # type: ignore
        config['value.deserializer'] = MessageObjDecoder() # type: ignore
        
        self.consumer = DeserializingConsumer(config)
        self.producer = Producer({
            'bootstrap.servers': broker,
            'message.max.bytes': 20971520,
            'batch.size': 20971520
        })
        self.consumer.subscribe([topic_in])
        self.topic_out = topic_out
        self.output_dir = output_dir
        self.model_path = model_path
        self.detector = YOLO(model_path)


    def run(self):
        signal.signal(signal.SIGTERM, signal_handler)
        string_serializer = StringSerializer('utf_8')

        try:
            while True:
                msg = self.consumer.poll(1.0) # type: ignore
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(msg.error())
                        break

                frame_number = msg.key()
                message = msg.value()

                processing_start_time = message.timestamp
                img_bytes = bytes.fromhex(message.frame_data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img = cv2.resize(img, (640, 640))
                
                file_label = f'frame_{frame_number}-{str(uuid.uuid4())}'
                current_date = datetime.today().date().isoformat()
                frame_filename = os.path.join(
                    f'{self.output_dir}', f'{current_date}/images', f'{file_label}.jpg')
                label_filename = os.path.join(
                    f'{self.output_dir}', f'{current_date}/labels', f'{file_label}.txt')
                
                cv2.imwrite(frame_filename, img)
                results = self.detector(img)
                detections, img = self.parse_result(img, results)
                # cv2.imshow("Image", img)
                self.save_yolo_labels(detections, label_filename, 640, 640)

                msg_out = MessageObjectOut(timestamp=processing_start_time,
                                     frame_data=img_bytes.hex(),
                                     detections = detections)

                self.producer.produce(self.topic_out, key=string_serializer(str(frame_number)), 
                    value=json.dumps(msg_out, cls=MessageObjEncoder).encode("utf-8"),
                    callback=delivery_callback)
                self.producer.poll(0)
        except KafkaException as e:
            print(f"Kafka error: {e}")
        except KeyboardInterrupt:
            print("Aborted by user")
        finally:
            self.consumer.close()
            self.producer.flush()
    
    def parse_result(self, img, results):
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                conf = math.ceil((box.conf[0]*100))/100
                cls = int(box.cls[0])
                class_name = classNames[cls]
                label = f'{class_name}{conf}'
                t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
                c2 = x1 + t_size[0], y1 - t_size[1] - 3
                cv2.rectangle(img, (x1, y1), c2, [255, 0, 255], -1, cv2.LINE_AA)
                cv2.putText(img, label, (x1, y1-2), 0, 1,
                            [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
                detections.append([cls, x1, y1, x2, y2])
        return detections, img


    def save_yolo_labels(self, detections, file_path, img_width, img_height):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as f:
            for detection in detections:
                class_id, x1, y1, x2, y2 = detection
                # Convert to YOLO format
                x_center = ((x1 + x2) / 2) / img_width
                y_center = ((y1 + y2) / 2) / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height
                f.write(f"{class_id} {x_center} {y_center} {width} {height}\n")

def parse_args():
    parser = argparse.ArgumentParser(
        description='Consume video frames from Kafka and detect objects')
    parser.add_argument('--topic-in', required=False,
                        help='Kafka topic to consume frames from')
    parser.add_argument('--topic-out', required=False,
                        help='Kafka topic to publish message to')
    parser.add_argument('--output_dir', required=False, default='/output',
                        help='Directory to save the detection results')
    parser.add_argument('--model_path', required=False, default='detector/models/best.pt',
                        help='Path to the model to use')
    return parser.parse_args()


def main():
    args = parse_args()
    topic_in = os.getenv('TOPIC_IN', args.topic_in)
    topic_out = os.getenv('TOPIC_OUT', args.topic_out)
    output_dir = os.getenv('OUTPUT_DIR', args.output_dir)
    model_path = os.getenv('MODEL_PATH', args.model_path)
    print(model_path)
    detector_service = DetectorService(broker, topic_in, topic_out, output_dir, model_path)
    detector_service.run()


if __name__ == '__main__':
    main()
