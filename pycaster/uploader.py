from pathlib import Path

import boto3


class Uploader:
    S3_KEY = 's3'
    PUBLIC_EXTRA_ARGS = {'ACL': 'public-read'}

    def __init__(self, region_name, endpoint_url, access_key, secret):
        self.session = self.init_session()
        self.client = self._init_client(region_name, endpoint_url, access_key, secret)

    def upload_file_publicly(self, file_location, upload_path, bucket):
        path = Path(file_location).resolve()

        return self.client.upload_file(
            str(path),
            str(bucket),
            f'{upload_path}/{str(path.name)}',
            ExtraArgs=self.PUBLIC_EXTRA_ARGS,
        )

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
