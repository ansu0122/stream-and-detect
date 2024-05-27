import os
import boto3
from concurrent.futures import ThreadPoolExecutor

class S3Connection:
    def __init__(self, bucket_name, max_workers=10):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name
        self.max_workers = max_workers

    def upload_files(self, local_folder, target_folder):
        files_to_upload = []
        for root, dirs, files in os.walk(local_folder):
            for file in files:
                file_path = os.path.join(root, file)
                files_to_upload.append(file_path)

        # upload files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            executor.map(self.upload_file)

        print('Files uploaded successfully')

    def upload_file(self, file_path):
        s3_key = os.path.join(target_folder, os.path.relpath(file_path, local_folder)).replace("\\", "/")
        self.s3.upload_file(file_path, self.bucket_name, s3_key)


if __name__ == '__main__':
    bucket_name = 'stream-n-detect'
    local_folder = 'data/'
    target_folder = 'datalake/'

    s3_connection = S3Connection(bucket_name)
    # s3_connection.upload_files(local_folder, target_folder)
    s3_connection.upload_file('data/data.yaml')
