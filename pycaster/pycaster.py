import json
import os
from pathlib import Path

import click

from database import Database, Episode
from feedgen.feed import FeedGenerator
from uploader import Uploader


class Pycaster:
    # General
    CONFIG_PATH = '../config.json'
    DATABASE_FILE = '../pycaster.db'
    MP3_MIME_TYPE = 'audio/mpeg'
    XML_RSS_MIME_TYPE = 'application/rss+xml'
    FEED_XML_FILE = 'feed.xml'

    # Configuration keys
    HOSTING_KEY = 'hosting'
    PODCAST_KEY = 'podcast'

    HOSTING_ACCESS_KEY_KEY = 'accessKey'
    HOSTING_DATABASE_PATH_KEY = 'databasePath'
    HOSTING_ENDPOINT_URL_KEY = 'endpointUrl'
    HOSTING_EPISODE_PATH_KEY = 'episodePath'
    HOSTING_FEED_PATH_KEY = 'feedPath'
    HOSTING_REGION_NAME_KEY = 'regionName'
    HOSTING_SECRET_KEY = 'secret'
    HOSTING_BUCKET_NAME_KEY = 'bucketName'

    AUTHOR_EMAIL_KEY = 'authorEmail'
    CATEGORY_KEY = 'category'
    DESCRIPTION_KEY = 'description'
    LANGUAGE_KEY = 'language'
    LOGO_URI_KEY = 'logoUri'
    NAME_KEY = 'name'
    WEBSITE_KEY = 'website'

    def __init__(self, episode_title, episode_description, episode_file_location):
        self._load_settings(episode_title, episode_description, episode_file_location)
        self.feed = self._generate_feed()
        self.db = self._init_db()

    def publish_new_episode(self):
        try:
            uploader = self._init_uploader()

            uploader.upload_file_publicly(
                file_location=self.episode_file_location,
                upload_path=self.hosting_episode_path,
                bucket=self.hosting_bucket,
                extra_args={Uploader.CONTENT_TYPE_KEY: self.MP3_MIME_TYPE},
                overwrite=False,
            )

            self._append_previous_episodes_to_feed()

            self._create_new_episode_entry(
                title=self.episode_title,
                description=self.episode_description,
                file_uri=self.episode_file_uri,
                file_type=self.MP3_MIME_TYPE,
                file_size=str(self.calculate_file_size(self.episode_file_location)),
            )

            self.feed.rss_file(self.FEED_XML_FILE, pretty=True)

            uploader.upload_file_publicly(
                file_location=self.FEED_XML_FILE,
                upload_path=self.hosting_feed_path,
                bucket=self.hosting_bucket,
                extra_args={Uploader.CONTENT_TYPE_KEY: self.XML_RSS_MIME_TYPE},
                overwrite=True,
            )

            self._delete_local_feed_file()

            uploader.upload_file_privately(
                file_location=self.DATABASE_FILE,
                upload_path=self.hosting_database_path,
                bucket=self.hosting_bucket,
                overwrite=True,
            )
        except Exception as exception:
            print(f"\nAn error occurred while uploading the new episode: '{repr(exception)}'")
            exit()

        print('\nEpisode successfully uploaded!')

    def _create_new_episode_entry(self, title, description, file_uri, file_type, file_size):
        episode = self.feed.add_entry()
        episode.id(file_uri)
        episode.title(title)
        episode.description(description)
        episode.enclosure(file_uri, file_size, file_type)

        self._insert_new_episode_into_database(
            Episode(
                title=title,
                description=description,
                file_uri=file_uri,
                file_type=file_type,
                file_size=file_size,
            )
        )

        return episode

    def _append_previous_episodes_to_feed(self):
        for previous_episode in self._retrieve_previous_episodes():
            episode = self.feed.add_entry()
            episode.id(previous_episode.file_uri)
            episode.title(previous_episode.title)
            episode.description(previous_episode.description)
            episode.enclosure(previous_episode.file_uri, previous_episode.file_size, previous_episode.file_type)

    def _insert_new_episode_into_database(self, episode: Episode):
        self.db.insert_new_episode(episode)

    def _retrieve_previous_episodes(self):
        return self.db.retrieve_all_episodes()

    def _generate_feed(self):
        feed = FeedGenerator()

        feed.load_extension('podcast')
        feed.podcast.itunes_category(self.category)

        feed.author({'email': self.author_email, 'name': self.name})
        feed.description(self.description)
        feed.language(self.language)
        feed.link(href=self.WEBSITE_KEY, rel='alternate')
        feed.logo(self.logo_uri)
        feed.title(self.name)

        return feed

    def _init_uploader(self):
        return Uploader(
            region_name=self.hosting_region,
            endpoint_url=self.hosting_endpoint_url,
            access_key=self.hosting_access_key,
            secret=self.hosting_secret,
        )

    def _init_db(self):
        db = Database(self.DATABASE_FILE)
        db.create_episode_database()
        return db

    def _delete_local_feed_file(self):
        os.remove(f'./{self.FEED_XML_FILE}')

    def _load_settings(self, episode_title, episode_description, episode_file_location):
        try:
            self.config = self._load_config()

            self.hosting_access_key = self._load_generic_hosting_config_field(self.HOSTING_ACCESS_KEY_KEY)
            self.hosting_database_path = self._load_generic_hosting_config_field(self.HOSTING_DATABASE_PATH_KEY)
            self.hosting_endpoint_url = self._load_generic_hosting_config_field(self.HOSTING_ENDPOINT_URL_KEY)
            self.hosting_episode_path = self._load_generic_hosting_config_field(self.HOSTING_EPISODE_PATH_KEY)
            self.hosting_feed_path = self._load_generic_hosting_config_field(self.HOSTING_FEED_PATH_KEY)
            self.hosting_region = self._load_generic_hosting_config_field(self.HOSTING_REGION_NAME_KEY)
            self.hosting_secret = self._load_generic_hosting_config_field(self.HOSTING_SECRET_KEY)
            self.hosting_bucket = self._load_generic_hosting_config_field(self.HOSTING_BUCKET_NAME_KEY)

            self.author_email = self._load_generic_podcast_config_field(self.AUTHOR_EMAIL_KEY)
            self.category = self._load_generic_podcast_config_field(self.CATEGORY_KEY)
            self.description = self._load_generic_podcast_config_field(self.DESCRIPTION_KEY)
            self.language = self._load_generic_podcast_config_field(self.LANGUAGE_KEY)
            self.logo_uri = self._load_generic_podcast_config_field(self.LOGO_URI_KEY)
            self.name = self._load_generic_podcast_config_field(self.NAME_KEY)
            self.website = self._load_generic_podcast_config_field(self.WEBSITE_KEY)

            self.episode_title = self.verify_episode_title(episode_title)
            self.episode_description = self.verify_episode_description(episode_description)
            self.episode_file_location = self.verify_episode_file_location(episode_file_location)

            self.episode_file_uri = self._build_episode_file_uri()
        except Exception as exception:
            print(f"\nAn error occurred while loading the configuration: '{repr(exception)}'")
            exit()

    def _load_generic_hosting_config_field(self, field_key):
        field = self.config.get(self.HOSTING_KEY, {}).get(field_key)

        if not field:
            raise self.build_missing_config_exception(f'{self.HOSTING_KEY}.{field_key}')

        return field

    def _load_generic_podcast_config_field(self, field_key):
        field = self.config.get(self.PODCAST_KEY, {}).get(field_key)

        if not field:
            raise self.build_missing_config_exception(f'{self.PODCAST_KEY}.{field_key}')

        return field

    def _load_config(self):
        with open(os.path.abspath(Path(self.CONFIG_PATH).resolve()), 'r') as file:
            config = json.loads(file.read())

            if not config:
                raise ImportError(f"A configuration file could not be found at the default path '{self.CONFIG_PATH}'")

            return config

    def _build_episode_file_uri(self):
        endpoint_protocol, raw_endpoint_url = self.remove_http_from_url(self.hosting_endpoint_url)
        return (
            f'{endpoint_protocol}://' +
            f'{self.hosting_bucket}.' +
            f'{raw_endpoint_url}/' +
            f'{self.hosting_episode_path}/' +
            f'{Path(self.episode_file_location).resolve().name}'
        )

    @staticmethod
    def verify_episode_title(episode_title):
        if not episode_title:
            raise ValueError("The episode title is missing")
        return episode_title

    @staticmethod
    def verify_episode_description(episode_description):
        if not episode_description:
            raise ValueError("The episode description is missing")
        return episode_description

    @staticmethod
    def verify_episode_file_location(episode_file_location):
        if not Path(episode_file_location).resolve().is_file():
            raise ValueError("The episode file is missing")
        return episode_file_location

    @staticmethod
    def build_missing_config_exception(json_path):
        return ValueError(f"The configuration file is missing information in the path: '{json_path}'")

    @staticmethod
    def build_illegal_configuration_exception(json_path):
        return ValueError(f"The value in path of the configuration file is illegal: '{json_path}'")

    @staticmethod
    def calculate_file_size(file_location):
        return Path(file_location).resolve().stat().st_size

    @staticmethod
    def remove_http_from_url(url):
        if 'http://' in url:
            protocol = 'http'
            url = url.replace(f'{protocol}://', '')
        elif 'https://' in url:
            protocol = 'https'
            url = url.replace(f'{protocol}://', '')
        return protocol, url

    @staticmethod
    @click.command()
    @click.option('--title', prompt='Enter the title of this episode')
    @click.option('--description', prompt='Enter the description of this episode')
    @click.option('--file', prompt='Enter the file location of this episode')
    def read_arguments(title, description, file):
        Pycaster(episode_title=title, episode_description=description, episode_file_location=file).publish_new_episode()


if __name__ == '__main__':
    Pycaster.read_arguments()
