# syntax=docker/dockerfile:1.4
# https://pythonspeed.com/articles/base-image-python-docker-images/
FROM python:3.10-slim

# set working directory to /app
WORKDIR /app

# copy the dependencies file  from current local to working dir of the image
COPY requirements.txt requirements.txt

# install cv2 dependencies
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# Install tkinter dependencies
RUN apt-get install -y python3-tk

# Install s3fs
RUN apt-get update && apt-get install -y s3fs fuse

# Copy the entrypoint script to the container
COPY entrypoint.sh /entrypoint.sh

# Ensure the entrypoint script is executable
RUN chmod +x /entrypoint.sh

# install dependencies form requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# moving code from current local to app image directory
ADD . /app

# container port exposed
EXPOSE 8000

# Run app.py when the container launches
# https://spacelift.io/blog/docker-entrypoint-vs-cmd
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "tracker.py"]