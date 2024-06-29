#!/bin/bash

# Check if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
  echo "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables must be set"
  exit 1
fi

# Create the credentials file
echo "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" > /etc/passwd-s3fs

# Set the correct permissions
chmod 600 /etc/passwd-s3fs

# Create the mount point directory if it doesn't exist
mkdir -p /mnt/s3

# Mount the S3 bucket
s3fs stream-n-detect /mnt/s3 -o passwd_file=/etc/passwd-s3fs,allow_other

# Execute the main command (run the Python application)
exec "$@"
