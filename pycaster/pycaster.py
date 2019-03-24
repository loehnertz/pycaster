import json
import os
from itertools import chain
from pathlib import Path

import click
from feedgen.feed import FeedGenerator

from uploader import Uploader


class Pycaster:
    # General
    CONFIG_PATH = '../config.json'
    MP3_TYPE_KEY = 'audio/mpeg'
    FEED_XML_FILE = 'feed.xml'

    # Configuration keys
    HOSTING_KEY = 'hosting'
    PODCAST_KEY = 'podcast'

    HOSTING_ACCESS_KEY_KEY = 'accessKey'
    HOSTING_ENDPOINT_URL_KEY = 'endpointUrl'
    HOSTING_EPISODE_PATH_KEY = 'episodePath'
    HOSTING_FEED_PATH_KEY = 'feedPath'
    HOSTING_REGION_NAME_KEY = 'regionName'
    HOSTING_SECRET_KEY = 'secret'
    HOSTING_BUCKET_NAME_KEY = 'bucketName'

    AUTHORS_KEY = 'authors'
    AUTHORS_EMAIL_KEY = 'email'
    AUTHORS_NAME_KEY = 'name'
    AUTHORS_URI_KEY = 'uri'
    CATEGORY_KEY = 'category'
    DESCRIPTION_KEY = 'description'
    LANGUAGE_KEY = 'language'
    LOGO_URI_KEY = 'logoUri'
    NAME_KEY = 'name'
    WEBSITE_KEY = 'website'

    def __init__(self, episode_title, episode_description, episode_file_location):
        self._load_settings(episode_title, episode_description, episode_file_location)
        self.feed = self._generate_feed()

    def publish_new_episode(self):
        uploader = self._init_uploader()

        uploader.upload_file_publicly(
            file_location=self.episode_file_location,
            upload_path=self.hosting_episode_path,
            bucket=self.hosting_bucket,
        )

        episode = self.feed.add_entry()
        episode.id(self.episode_file_uri)
        episode.title(self.episode_title)
        episode.description(self.episode_description)
        episode.enclosure(
            self.episode_file_uri,
            str(self.calculate_file_size(self.episode_file_location)),
            self.MP3_TYPE_KEY,
        )

        self.feed.rss_file(self.FEED_XML_FILE, pretty=True)

        uploader.upload_file_publicly(
            file_location=self.FEED_XML_FILE,
            upload_path=self.hosting_feed_path,
            bucket=self.hosting_bucket,
        )

        self._delete_local_feed_file()

        print('\nEpisode successfully uploaded!')

    def _generate_feed(self):
        feed = FeedGenerator()

        feed.load_extension('podcast')
        feed.podcast.itunes_category(self.category)

        feed.author(self.authors)
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

    def _delete_local_feed_file(self):
        os.remove(f'./{self.FEED_XML_FILE}')

    def _load_settings(self, episode_title, episode_description, episode_file_location):
        try:
            self.config = self._load_config()

            self.hosting_access_key = self._load_generic_hosting_config_field(self.HOSTING_ACCESS_KEY_KEY)
            self.hosting_endpoint_url = self._load_generic_hosting_config_field(self.HOSTING_ENDPOINT_URL_KEY)
            self.hosting_episode_path = self._load_generic_hosting_config_field(self.HOSTING_EPISODE_PATH_KEY)
            self.hosting_feed_path = self._load_generic_hosting_config_field(self.HOSTING_FEED_PATH_KEY)
            self.hosting_region = self._load_generic_hosting_config_field(self.HOSTING_REGION_NAME_KEY)
            self.hosting_secret = self._load_generic_hosting_config_field(self.HOSTING_SECRET_KEY)
            self.hosting_bucket = self._load_generic_hosting_config_field(self.HOSTING_BUCKET_NAME_KEY)

            self.authors = self._load_authors()
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
            print(f"An error occurred while loading the configuration: '{repr(exception)}'")
            exit()

    def _load_authors(self):
        authors = self.config.get(self.PODCAST_KEY, {}).get(self.AUTHORS_KEY)

        if not authors:
            raise self.build_missing_config_exception(self.AUTHORS_KEY)

        authors_keys = list(chain(*[list(author.keys()) if isinstance(author, dict) else None for author in authors]))

        if not all(authors_keys):
            raise self.build_missing_config_exception(f'{self.AUTHORS_KEY}.{self.AUTHORS_NAME_KEY}')

        for key in authors_keys:
            if key not in [self.AUTHORS_EMAIL_KEY, self.AUTHORS_NAME_KEY, self.AUTHORS_URI_KEY]:
                raise self.build_illegal_configuration_exception(f'{self.AUTHORS_KEY}.{key}')

        return authors

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
        return f'{endpoint_protocol}://{raw_endpoint_url}/{Path(self.episode_file_location).resolve().name}'

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
