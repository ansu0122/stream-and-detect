import os
import sys
import signal
import argparse
import json
from datetime import datetime
import cv2
from confluent_kafka import Producer, KafkaException
from confluent_kafka.serialization import StringSerializer
from adminapi import create_topic


class MessageObj(object):
    def __init__(self, timestamp=None, frame_data=None):
        self.timestamp = timestamp
        self.frame_data = frame_data


class MessageObjEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, MessageObj):
            return {
                'timestamp': obj.timestamp,
                'frame_data': obj.frame_data
            }
        else:
            return super().default(obj)


def signal_handler(sig, frame):
    print("Received SIGTERM, shutting down gracefully...")
    sys.exit(0)


def produce_messages(broker, topic, video_path):

    signal.signal(signal.SIGTERM, signal_handler)

    p = Producer({'bootstrap.servers': broker,
                  'message.max.bytes': 20971520,
                  'batch.size': 20971520
                  })

    string_serializer = StringSerializer('utf_8')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return
    try:
        frame_number = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_number += 1
            _, img_encoded = cv2.imencode('.jpg', frame)
            timestamp = datetime.now().isoformat()

            msg = MessageObj(timestamp=timestamp, frame_data=img_encoded.tobytes().hex())
            p.produce(topic, key=string_serializer(str(frame_number)),
                        value=json.dumps(
                            msg, cls=MessageObjEncoder).encode("utf-8"),
                        callback=delivery_callback)

            p.poll(0)
    except KafkaException as e:
        print(f"Kafka error: {e}")
    except KeyboardInterrupt:
        print("Aborted by user")
    finally:
        p.flush()

    cap.release()


def delivery_callback(err, msg):
    if err is not None:
        print("Delivery failed to {} topic {}: {}".format(
            msg.topic(), msg.key(), err))
        return
    print('Message {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Stream video frames to Kafka')
    parser.add_argument('--broker', required=False, default='broker:9092',
                        help='Kafka broker')
    parser.add_argument('--topic-detect', required=False, default='traffic',
                        help='Kafka topic to subscribed by detector')
    parser.add_argument('--partitions-detect', required=False, default=1,
                        help='Number of partitions for detector topic')
    parser.add_argument('--video-dir', required=False, default='video/',
                        help='Directory with video file(s)')
    
    return parser.parse_args()


def find_video_file(video_dir):
    for root, _, files in os.walk(video_dir):
        for file in files:
            if file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                return os.path.join(root, file)
    return None


def main():
    args = parse_args()
    broker = os.getenv('BROKER', args.broker)
    topic_detect = os.getenv('TOPIC_DETECT', args.topic_detect)
    partitions_detect = os.getenv('PARTITIONS_DETECT', args.partitions_detect)
    video_dir = os.getenv('VIDEO_DIR', args.video_dir)
    video_file = find_video_file(video_dir)
    if not video_file:
        raise Exception(
            "Please provide a video file in the specified directory")
    create_topic(broker, topic_detect, num_partitions=int(partitions_detect))

    produce_messages(broker, topic_detect, video_file)


if __name__ == '__main__':
    main()
