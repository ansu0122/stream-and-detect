import json
import math
import argparse
import os
import sys
import uuid
import signal
from functools import reduce
import numpy as np
from datetime import datetime
from confluent_kafka import DeserializingConsumer, Producer, KafkaError, KafkaException
from confluent_kafka.serialization import StringSerializer, StringDeserializer
import cv2
from ultralytics import YOLO, solutions


class MessageObj(object):
    def __init__(self, timestamp, frame_data):
        self.timestamp = timestamp
        self.frame_data = frame_data


class MessageObjDecoder:
    def __call__(self, value, ctx):
        data = json.loads(value.decode("utf-8"))
        return MessageObj(timestamp=datetime.fromisoformat(data['timestamp']),
                          frame_data=data['frame_data'])


def signal_handler(sig, frame):
    print("Received SIGTERM, shutting down gracefully...")
    sys.exit(0)


def delivery_callback(err, msg):
    if err is not None:
        print("Delivery failed to {} topic at {} for {} with {} offset: {}".format(
            msg.topic(), msg.partition(), msg.key(), msg.offset(), err))
        return


class TrackerService:

    def __init__(self, broker, topic_in, output_dir, model_path, classes_to_count, w=1920, h=1080, fps=30):

        config = {
            'bootstrap.servers': broker,
            'group.id': 'tracker-group',
            'auto.offset.reset': 'earliest',
            'fetch.message.max.bytes': 20971520,
            'max.partition.fetch.bytes': 20971520
        }
        config['key.deserializer'] = StringDeserializer()  # type: ignore
        config['value.deserializer'] = MessageObjDecoder()  # type: ignore

        self.consumer = DeserializingConsumer(config)
        self.consumer.subscribe([topic_in])
        self.output_dir = output_dir
        self.tracker = YoloTracker(model_path, classes_to_count, w, h)
        os.makedirs(self.output_dir, exist_ok=True)
        self.video_writer = cv2.VideoWriter(os.path.join(self.output_dir, "object_counting.mp4"),
                                            cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))  # type: ignore
        self.result_file = os.path.join(
            self.output_dir, "object_counting.json")
        self.previous_sum = 0

    def run(self):

        try:
            signal.signal(signal.SIGTERM, signal_handler)
            while True:
                msg = self.consumer.poll(1.0)  # type: ignore
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

                img = self.tracker.count(img)
                self.video_writer.write(img)
                self.video_writer.release()

                counts = self.tracker.get_result()
                new_sum = reduce(lambda acc, val: acc + sum(val.values()), counts.values(), 0)
                if new_sum != self.previous_sum:
                    with open(self.result_file, 'w') as json_file:
                        json.dump(counts, json_file, indent=4)
                    self.previous_sum = new_sum

        except KafkaException as e:
            print(f"Kafka error: {e}")
        except KeyboardInterrupt:
            print("Aborted by user")
        finally:
            self.consumer.close()
            self.video_writer.release()


class YoloTracker:

    def __init__(self, model_path, classes_to_count, w, h):

        self.model = YOLO(model_path)
        self.classes_to_count = classes_to_count
        self.line_points = [(w // 5, h // 2), (w - (w // 5), h // 2)]
        self.counter = solutions.ObjectCounter(
            view_img=False,
            reg_pts=self.line_points,
            classes_names=self.model.names,
            draw_tracks=True,
            line_thickness=2,
        )

    def count(self, img):
        tracks = self.model.track(
            img, persist=True, show=False, classes=self.classes_to_count)
        img = self.counter.start_counting(img, tracks)
        return img

    def get_result(self):
        return self.counter.class_wise_count


def parse_args():
    parser = argparse.ArgumentParser(
        description='Consume video frames from Kafka and counts objects')
    parser.add_argument('--broker', required=False, default='broker:9092',
                        help='Kafka broker')
    parser.add_argument('--topic-in', required=False, default='traffic',
                        help='Kafka topic to consume frames from')
    parser.add_argument('--output_dir', required=False, default='output/',
                        help='Directory to save the detection results')
    parser.add_argument('--model_path', required=False, default='tracker/models/best.pt',
                        help='Path to the model to use')
    parser.add_argument('--classes-to-count', required=False, default='[2,3]',
                        help='Object classes to count')
    return parser.parse_args()


def main():
    args = parse_args()
    broker = os.getenv('BROKER', args.broker)
    topic_in = os.getenv('TOPIC_IN', args.topic_in)
    output_dir = os.getenv('OUTPUT_DIR', args.output_dir)
    model_path = os.getenv('MODEL_PATH', args.model_path)
    classes_to_count = json.loads(
        os.getenv('CLASSES_TO_COUNT', args.classes_to_count))
    tracker_service = TrackerService(
        broker, topic_in, output_dir, model_path, classes_to_count)
    tracker_service.run()


if __name__ == '__main__':
    main()
