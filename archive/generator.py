import requests
import cv2
import os
import uuid
import math
import pickle

classNames = ['bicycle', 'bus', 'car', 'motorbike', 'person']
video_path = 'trainer/data/video/cars.mp4'
output_folder = 'trainer/data/output/'
post_url = 'http://127.0.0.1:8000/detect'


def generate_video_stream(video_path):

    output_path = f'{output_folder}{os.path.basename(video_path)}'
    if not os.path.exists(output_path):
        os.makedirs(f'{output_path}/images')
        os.makedirs(f'{output_path}/labels')
        os.makedirs(f'{output_path}/video')

    video_capture = video_path
    cap = cv2.VideoCapture(video_capture)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    out = cv2.VideoWriter(f'{output_path}/video/output.mp4v', cv2.VideoWriter_fourcc( # type: ignore
        'M', 'J', 'P', 'G'), 10, (frame_width, frame_height))
    frame_count = 0
    while True:
        success, img = cap.read()
        if (not (success)):
            break
        img = cv2.resize(img, (640, 640))
        file_label = f'{os.path.basename(video_path)}-frame_{frame_count}-{str(uuid.uuid4())}'
        frame_filename = os.path.join(
            f'{output_path}/images', f'{file_label}.jpg')
        cv2.imwrite(frame_filename, img)

        # Encode the image to memory
        _, img_encoded = cv2.imencode('.jpg', img)
        img_bytes = img_encoded.tobytes()

        # Make the POST request with the image data
        files = {'file': ('frame.jpg', img_bytes, 'image/jpeg')}
        response = requests.request('POST', post_url, files=files)

        if response.status_code == 200:
            results = pickle.loads(response.content)
            detections, img = parse_result(img, results)
            label_filename = os.path.join(
                f'{output_path}/labels', f'{file_label}.txt')
            save_yolo_labels(detections, label_filename, 640, 640)
        else:
            print(
                f'Failed to upload frame {frame_count}: {response.status_code}, {response.text}')

        frame_count += 1

        out.write(img)
        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('1'):
            break
    out.release()


def parse_result(img, results):
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


def save_yolo_labels(detections, file_path, img_width, img_height):
    with open(file_path, 'w') as f:
        for detection in detections:
            class_id, x1, y1, x2, y2 = detection
            # Convert to YOLO format
            x_center = ((x1 + x2) / 2) / img_width
            y_center = ((y1 + y2) / 2) / img_height
            width = (x2 - x1) / img_width
            height = (y2 - y1) / img_height
            f.write(f"{class_id} {x_center} {y_center} {width} {height}\n")


if __name__ == "__main__":
    generate_video_stream(video_path)
