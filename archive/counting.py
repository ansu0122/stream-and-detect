import cv2
from ultralytics import YOLO, solutions

model = YOLO("tracker/models/best.pt")

cap = cv2.VideoCapture("video/Brasil7.mp4")
assert cap.isOpened(), "Error reading video file"
w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

line_points = [(w // 20, h // 2), (w - (w // 20), h // 2)]
classes_to_count = [2, 3]  # person and car classes for count

# Video writer
video_writer = cv2.VideoWriter("object_counting_output.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)) # type: ignore

# Init Object Counter
counter = solutions.ObjectCounter(
    view_img=True,
    reg_pts=line_points,
    classes_names=model.names,
    draw_tracks=True,
    line_thickness=2,
)

while cap.isOpened():
    success, img = cap.read()
    if not success:
        print("Video frame is empty or video processing has been successfully completed.")
        break
    # img = cv2.resize(img, (640, 640))
    tracks = model.track(img, persist=True, show=False, classes=classes_to_count)
    img = counter.start_counting(img, tracks)

    # img = cv2.resize(img, (w, h))
    video_writer.write(img)


print(counter.class_wise_count)

cap.release()
video_writer.release()
cv2.destroyAllWindows()