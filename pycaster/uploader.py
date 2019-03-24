from pathlib import Path

import boto3
from botocore.exceptions import ClientError


class Uploader:
    S3_KEY = 's3'
    PUBLIC_EXTRA_ARGS = {'ACL': 'public-read'}

    def __init__(self, region_name, endpoint_url, access_key, secret):
        self.session = self.init_session()
        self.client = self._init_client(region_name, endpoint_url, access_key, secret)

    def upload_file_publicly(self, file_location, upload_path, bucket, overwrite=False):
        path = Path(file_location).resolve()
        file_upload_path = f'{upload_path}/{str(path.name)}'

        if overwrite is False and self._file_already_exists(file_upload_path, bucket):
            raise FileExistsError(f"The file at upload path '{file_upload_path}' already exists")

        return self.client.upload_file(
            str(path),
            str(bucket),
            file_upload_path,
            ExtraArgs=self.PUBLIC_EXTRA_ARGS,
        )

    def _file_already_exists(self, file_path, bucket):
        try:
            self.client.head_object(Key=file_path, Bucket=bucket)
            return True
        except ClientError:
            return False

    def _init_client(self, region_name, endpoint_url, access_key, secret_key):
        return self.session.client(
            service_name=self.S3_KEY,
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    @staticmethod
    def init_session():
        return boto3.session.Session()
