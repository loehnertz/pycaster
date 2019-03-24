import json
import os
from itertools import chain
from pathlib import Path

import click
from feedgen.feed import FeedGenerator


class Pycaster:
    # General
    CONFIG_PATH = '../config.json'
    MP3_TYPE_KEY = 'audio/mpeg'

    # Configuration keys
    HOSTING_KEY = 'hosting'
    PODCAST_KEY = 'podcast'
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
        with open(os.path.abspath(Path(self.episode_file_location).resolve()), 'r') as file:
            episode_file_uri = None

        episode = self.feed.add_entry()
        episode.id(episode_file_uri)
        episode.title(self.episode_title)
        episode.description(self.episode_description)
        episode.enclosure(episode_file_uri, self.calculate_file_size(self.episode_file_location), self.MP3_TYPE_KEY)

        print(self.feed.rss_str())

    def _generate_feed(self):
        feed = FeedGenerator()

        feed.load_extension('podcast')
        feed.podcast.itunes_category(self.CATEGORY_KEY)

        feed.author(self.authors)
        feed.description(self.description)
        feed.language(self.language)
        feed.link(href=self.WEBSITE_KEY, rel='alternate')
        feed.logo(self.logo_uri)
        feed.title(self.name)

        return feed

    def _load_settings(self, episode_title, episode_description, episode_file_location):
        try:
            self.config = self._load_config()
            self.authors = self._load_authors()
            self.category = self._load_category()
            self.description = self._load_description()
            self.language = self._load_language()
            self.logo_uri = self._load_logo_uri()
            self.name = self._load_name()
            self.website = self._load_website()
            self.episode_title = self.verify_episode_title(episode_title)
            self.episode_description = self.verify_episode_description(episode_description)
            self.episode_file_location = self.verify_episode_file_location(episode_file_location)
        except Exception as exception:
            print(f"An error occurred while loading the configuration: '{repr(exception)}'")
            exit()

    def _load_authors(self):
        authors = self.config.get(self.PODCAST_KEY, {}).get(self.AUTHORS_KEY)

        if not authors:
            raise self.build_missing_config_exception(self.AUTHORS_KEY)

        authors_keys = list(chain(*[list(author.keys()) if isinstance(author, dict) else None for author in authors]))

        if not all(authors_keys):
            raise self.build_missing_config_exception(f"{self.AUTHORS_KEY}.{self.AUTHORS_NAME_KEY}")

        for key in authors_keys:
            if key not in [self.AUTHORS_EMAIL_KEY, self.AUTHORS_NAME_KEY, self.AUTHORS_URI_KEY]:
                raise self.build_illegal_configuration_exception(f"{self.AUTHORS_KEY}.{key}")

        return authors

    def _load_category(self):
        return self._load_generic_podcast_config_field(self.CATEGORY_KEY)

    def _load_description(self):
        return self._load_generic_podcast_config_field(self.DESCRIPTION_KEY)

    def _load_language(self):
        return self._load_generic_podcast_config_field(self.LANGUAGE_KEY)

    def _load_logo_uri(self):
        return self._load_generic_podcast_config_field(self.LOGO_URI_KEY)

    def _load_name(self):
        return self._load_generic_podcast_config_field(self.NAME_KEY)

    def _load_website(self):
        return self._load_generic_podcast_config_field(self.WEBSITE_KEY)

    def _load_generic_podcast_config_field(self, field_key):
        field = self.config.get(self.PODCAST_KEY, {}).get(field_key)

        if not field:
            raise self.build_missing_config_exception(field_key)

        return field

    def _load_config(self):
        with open(os.path.abspath(Path(self.CONFIG_PATH).resolve()), 'r') as file:
            config = json.loads(file.read())

            if not config:
                raise ImportError(f"A configuration file could not be found at the default path '{self.CONFIG_PATH}'")

            return config

    @staticmethod
    def verify_episode_title(episode_title):
        if not episode_title:
            raise ValueError("The episode title is missing")

    @staticmethod
    def verify_episode_description(episode_description):
        if not episode_description:
            raise ValueError("The episode description is missing")

    @staticmethod
    def verify_episode_file_location(episode_file_location):
        if not Path(episode_file_location).resolve().is_file():
            raise ValueError("The episode file is missing")

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
    @click.command()
    @click.option('--title', prompt='Enter the title of this episode')
    @click.option('--description', prompt='Enter the description of this episode')
    @click.option('--file', prompt='Enter the file location of this episode')
    def read_arguments(title, description, file):
        Pycaster(episode_title=title, episode_description=description, episode_file_location=file).publish_new_episode()


if __name__ == '__main__':
    Pycaster.read_arguments()
