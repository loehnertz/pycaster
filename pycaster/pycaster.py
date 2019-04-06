import html
import json
import os
import re
from datetime import datetime
from pathlib import Path

import click
import pytz
from feedgen.feed import FeedGenerator

from database import Database, Episode
from uploader import Uploader


class Pycaster:
    # General
    CONFIG_PATH = '../config.json'
    DATABASE_FILE = '../pycaster.db'
    MP3_MIME_TYPE = 'audio/mpeg'
    XML_MIME_TYPE = 'text/xml'
    FEED_XML_FILE = 'feed.xml'
    DEFAULT_TIMEZONE_KEY = 'Europe/Amsterdam'
    HTML_TAG_REGEX = r'(<!--.*?-->|<[^>]*>)'

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

    AUTHOR_KEY = 'author'
    CATEGORY_KEY = 'category'
    DESCRIPTION_KEY = 'description'
    IS_EXPLICIT_KEY = 'explicit'
    LANGUAGE_KEY = 'language'
    LOGO_URI_KEY = 'logoUri'
    NAME_KEY = 'name'
    SUBTITLE_KEY = 'subtitle'
    WEBSITE_KEY = 'website'

    def __init__(
        self,
        republish,
        episode_title,
        episode_description,
        episode_duration,
        episode_file_location,
        episode_is_explicit,
    ):
        self._load_settings(
            republish=republish,
            episode_title=episode_title,
            episode_description=episode_description,
            episode_duration=episode_duration,
            episode_file_location=episode_file_location,
            episode_is_explicit=episode_is_explicit,
        )
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

            print('\nEpisode successfully uploaded!')

            self._append_previous_episodes_to_feed()

            self._create_new_episode_entry(
                description=self.convert_to_character_data(self.episode_description),
                duration=self.episode_duration,
                file_uri=self.episode_file_uri,
                file_type=self.MP3_MIME_TYPE,
                file_size=str(self.calculate_file_size(self.episode_file_location)),
                is_explicit=self.episode_is_explicit,
                published=datetime.now(pytz.timezone(self.DEFAULT_TIMEZONE_KEY)),
                title=self.episode_title,
            )

            self.feed.rss_file(self.FEED_XML_FILE, pretty=True)

            uploader.upload_file_publicly(
                file_location=self.FEED_XML_FILE,
                upload_path=self.hosting_feed_path,
                bucket=self.hosting_bucket,
                extra_args={Uploader.CONTENT_TYPE_KEY: self.XML_MIME_TYPE},
                overwrite=True,
            )

            self._delete_local_feed_file()

            print('\nFeed successfully updated!')

            uploader.upload_file_privately(
                file_location=self.DATABASE_FILE,
                upload_path=self.hosting_database_path,
                bucket=self.hosting_bucket,
                overwrite=True,
            )

            print('\nDatabase successfully backed-up!')
        except Exception as exception:
            print(f"\nAn error occurred while uploading the new episode: '{repr(exception)}'")
            exit()

        print('\nFinished!')

    def republish_episodes(self):
        try:
            uploader = self._init_uploader()

            self._append_previous_episodes_to_feed()

            self.feed.rss_file(self.FEED_XML_FILE, pretty=True)

            uploader.upload_file_publicly(
                file_location=self.FEED_XML_FILE,
                upload_path=self.hosting_feed_path,
                bucket=self.hosting_bucket,
                extra_args={Uploader.CONTENT_TYPE_KEY: self.XML_MIME_TYPE},
                overwrite=True,
            )

            self._delete_local_feed_file()

            print('\nFeed successfully updated!')

            uploader.upload_file_privately(
                file_location=self.DATABASE_FILE,
                upload_path=self.hosting_database_path,
                bucket=self.hosting_bucket,
                overwrite=True,
            )

            print('\nDatabase successfully backed-up!')
        except Exception as exception:
            print(f"\nAn error occurred while re-publishing the episodes: '{repr(exception)}'")
            exit()

        print('\nFinished!')

    def _create_new_episode_entry(
        self, title, description, duration, file_uri, file_type, file_size, is_explicit, published,
    ):
        episode = self._create_episode_entry(
            description=description,
            duration=duration,
            file_size=file_size,
            file_type=file_type,
            file_uri=file_uri,
            is_explicit=is_explicit,
            published=published,
            title=title,
        )

        self._insert_new_episode_into_database(
            Episode(
                title=title,
                description=description,
                duration=duration,
                file_uri=file_uri,
                file_type=file_type,
                file_size=file_size,
                is_explicit=is_explicit,
                published=published,
            ),
        )

        return episode

    def _create_episode_entry(
        self, description, duration, file_size, file_type, file_uri, is_explicit, published, title,
    ):
        episode = self.feed.add_entry()

        episode.podcast.itunes_author(self.author)
        episode.podcast.itunes_explicit(is_explicit)
        episode.podcast.itunes_duration(duration)
        episode.podcast.itunes_summary(self._convert_episode_itunes_summary(description))

        episode.description(description)
        episode.enclosure(file_uri, file_size, file_type)
        episode.id(file_uri)
        episode.published(published)
        episode.title(title)

        return episode

    def _append_previous_episodes_to_feed(self):
        for previous_episode in self._retrieve_previous_episodes():
            self._create_episode_entry(
                description=previous_episode.description,
                duration=previous_episode.duration,
                file_size=previous_episode.file_size,
                file_type=previous_episode.file_type,
                file_uri=previous_episode.file_uri,
                is_explicit=previous_episode.is_explicit,
                published=previous_episode.published,
                title=previous_episode.title,
            )

    def _insert_new_episode_into_database(self, episode: Episode):
        self.db.insert_new_episode(episode)

    def _retrieve_previous_episodes(self):
        return self.db.retrieve_all_episodes()

    def _generate_feed(self):
        feed = FeedGenerator()

        feed.load_extension('podcast')
        feed.podcast.itunes_author(self.author)
        feed.podcast.itunes_category(self.category)
        feed.podcast.itunes_explicit(self.is_explicit)
        feed.podcast.itunes_image(self.logo_uri)
        feed.podcast.itunes_subtitle(self.subtitle)
        feed.podcast.itunes_summary(self.description)

        feed.author(email=self.author, name=self.author)
        feed.description(self.description)
        feed.language(self.language)
        feed.link(href=self.website, rel='alternate')
        feed.logo(self.logo_uri)
        feed.subtitle(self.subtitle)
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

    def _load_settings(
        self,
        republish,
        episode_title,
        episode_description,
        episode_duration,
        episode_file_location,
        episode_is_explicit,
    ):
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

            self.author = self._load_generic_podcast_config_field(self.AUTHOR_KEY)
            self.category = self._load_generic_podcast_config_field(self.CATEGORY_KEY)
            self.description = self._load_generic_podcast_config_field(self.DESCRIPTION_KEY)
            self.is_explicit = self._load_generic_podcast_config_field(self.IS_EXPLICIT_KEY)
            self.language = self._load_generic_podcast_config_field(self.LANGUAGE_KEY)
            self.logo_uri = self._load_generic_podcast_config_field(self.LOGO_URI_KEY)
            self.name = self._load_generic_podcast_config_field(self.NAME_KEY)
            self.subtitle = self._load_generic_podcast_config_field(self.SUBTITLE_KEY)
            self.website = self._load_generic_podcast_config_field(self.WEBSITE_KEY)

            if not republish:
                self.episode_title = self.verify_episode_title(episode_title)
                self.episode_description = self._extract_episode_description(episode_description)
                self.episode_duration = self.verify_episode_duration(episode_duration)
                self.episode_file_location = self.verify_episode_file_location(episode_file_location)
                self.episode_is_explicit = self.verify_episode_is_explicit(episode_is_explicit)

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

    def _extract_episode_description(self, description_input):
        description_input = self.verify_episode_description(description_input)

        if Path(description_input).resolve().is_file():
            with open(os.path.abspath(Path(description_input).resolve()), 'r') as file:
                return ' '.join(str(file.read()).replace('\n', '').split())
        else:
            return description_input

    def _convert_episode_itunes_summary(self, summary):
        summary = str(html.unescape(summary)).replace('<br>', '\r\n').replace('<p>', '\r\n').replace('</p>', '\r\n')
        return re.compile(self.HTML_TAG_REGEX).sub('', summary)

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
    def verify_episode_duration(episode_duration):
        if not episode_duration:
            raise ValueError("The episode description is missing")
        return episode_duration

    @staticmethod
    def verify_episode_file_location(episode_file_location):
        if not Path(episode_file_location).resolve().is_file():
            raise ValueError("The episode file is missing")
        return episode_file_location

    @staticmethod
    def verify_episode_is_explicit(episode_is_explicit):
        if not episode_is_explicit:
            raise ValueError("The information if the episode contains explicit content is missing")
        return episode_is_explicit

    @staticmethod
    def build_missing_config_exception(json_path):
        return ValueError(f"The configuration file is missing information in the path: '{json_path}'")

    @staticmethod
    def build_illegal_configuration_exception(json_path):
        return ValueError(f"The value in path of the configuration file is illegal: '{json_path}'")

    @staticmethod
    def convert_to_character_data(content):
        return f"<![CDATA[{Pycaster.remove_unnecessary_spaces_from_html(html.escape(content))}]]>"

    @staticmethod
    def remove_unnecessary_spaces_from_html(html_string):
        return str(html_string).replace('<p> ', '<p>').replace('</p> ', '</p>').replace('<br> ', '<br>')

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
    @click.option('--republish', default=False)
    @click.option('--title', prompt='Enter the title of this episode')
    @click.option('--description', prompt='Enter the description of this episode (can be path to a text file)')
    @click.option('--explicit', prompt='Enter "yes" or "no" regarding the the episode being explicit')
    @click.option('--duration', prompt='Enter the duration (mm:ss) of this episode')
    @click.option('--file', prompt='Enter the file location of this episode')
    def read_arguments(republish, title, description, explicit, duration, file):
        pycaster = Pycaster(
            republish=republish,
            episode_title=title,
            episode_description=description,
            episode_duration=duration,
            episode_file_location=file,
            episode_is_explicit=explicit,
        )

        if republish:
            pycaster.republish_episodes()
        else:
            pycaster.publish_new_episode()


if __name__ == '__main__':
    Pycaster.read_arguments()
