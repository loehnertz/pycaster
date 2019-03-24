import json
import os
from itertools import chain
from pathlib import Path

import click
from feedgen.feed import FeedGenerator


class Pycaster:
    # General
    CONFIG_PATH = '../config.json'

    # Configuration keys
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

    def __init__(self, episode_title, episode_file_location):
        self._load_settings(episode_title=episode_title, episode_file_location=episode_file_location)
        self.feed = self._generate_feed()

    def publish_new_episode(self):
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

    def _load_settings(self, episode_title, episode_file_location):
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
            self.episode_file_location = self.verify_episode_file_location(episode_file_location)
        except Exception as exception:
            print(f"An error occurred while loading the configuration: '{repr(exception)}'")
            exit()

    def _load_authors(self):
        authors = self.config.get(self.AUTHORS_KEY)

        if not authors:
            raise self.build_missing_configuration_exception(self.AUTHORS_KEY)

        authors_keys = list(chain(*[list(author.keys()) if isinstance(author, dict) else None for author in authors]))

        if not all(authors_keys):
            raise self.build_missing_configuration_exception(f"{self.AUTHORS_KEY}.{self.AUTHORS_NAME_KEY}")

        for key in authors_keys:
            if key not in [self.AUTHORS_EMAIL_KEY, self.AUTHORS_NAME_KEY, self.AUTHORS_URI_KEY]:
                raise self.build_illegal_configuration_exception(f"{self.AUTHORS_KEY}.{key}")

        return authors

    def _load_category(self):
        return self._load_generic_configuration_field(self.CATEGORY_KEY)

    def _load_description(self):
        return self._load_generic_configuration_field(self.DESCRIPTION_KEY)

    def _load_language(self):
        return self._load_generic_configuration_field(self.LANGUAGE_KEY)

    def _load_logo_uri(self):
        return self._load_generic_configuration_field(self.LOGO_URI_KEY)

    def _load_name(self):
        return self._load_generic_configuration_field(self.NAME_KEY)

    def _load_website(self):
        return self._load_generic_configuration_field(self.WEBSITE_KEY)

    def _load_generic_configuration_field(self, field_key):
        field = self.config.get(field_key)

        if not field:
            raise self.build_missing_configuration_exception(field_key)

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
    def verify_episode_file_location(episode_file_location):
        if not Path(episode_file_location).resolve().is_file():
            raise ValueError("The episode file is missing")

    @staticmethod
    def build_missing_configuration_exception(json_path):
        return ValueError(f"The configuration file is missing information in the path: '{json_path}'")

    @staticmethod
    def build_illegal_configuration_exception(json_path):
        return ValueError(f"The value in path of the configuration file is illegal: '{json_path}'")

    @staticmethod
    @click.command()
    @click.option('--title', prompt='Enter the title of this episode')
    @click.option('--file', prompt='Enter the file location of this episode')
    def read_arguments(title, file):
        Pycaster(episode_title=title, episode_file_location=file).publish_new_episode()


if __name__ == '__main__':
    Pycaster.read_arguments()
