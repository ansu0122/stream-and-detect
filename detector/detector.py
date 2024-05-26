from flask import Flask, Response, jsonify, request
import pickle
from ultralytics import YOLO
import cv2
import numpy as np

app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    return "Service is up and running", 200


@app.route('/detect', methods=['POST'])
def video():
    try:
        file = request.files['file']
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        detection_results = video_detection(img)
        return Response(pickle.dumps(detection_results), mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def video_detection(img):
    model = YOLO("models/best.pt")
    results = model(img)
    return results


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
