# pycaster
A tool for the automated generation of podcast feeds with a built-in upload functionality for new episodes


## Features

- Upload your freshly produced podcast episode via an interactive CLI
- Alternatively, use arguments when interacting with the CLI
- Automagically create a podcast feed via episode uploads and keep it updated with each new upload
- Supports `AWS S3`, `Google Cloud Storage`, `Digital Ocean Spaces`, and every other provider that is `AWS S3` API-compatible
- Automatically creates backups of the local episode database which is used for generating the feed
- Offers built-in protection against overwriting episodes that were already uploaded in the past
- Allows to use HTML markup in the description of an episode


## Motivation

I produce a podcast myself ([shameless plug][gist-of-it]),
so naturally I needed a tool to upload new episodes to my hosting provider.
As I am not a big fan of Wordpress, I did not want to go down that route that
is understandibly quite popular with podcast producers.
Instead I wanted something for the command-line, could not find anything and created my own instead.


## Configuration

First, duplicate the `config.template.json` to a file with the name `config.json`.    
Next, populate the `config.json` file with your information.

### Remarks

The `hosting` object:
- `accessKey`: Look up the documentation of your hosting provider regarding AWS S3 API compatibility.
  In `AWS S3`, it is called `aws_access_key_id`.
- `secret`: Look up the documentation of your hosting provider regarding AWS S3 API compatibility.
  In `AWS S3`, it is called `aws_secret_access_key`.
- `databasePath`, `episodePath`, `feedPath`: Correspond to the paths in the bucket of the hosting provider
  as relative paths from the `bucketName` root.
- `endpointUrl`, `regionName`: Have to be looked up in the hosting providers documentation, this is necessary
  as per AWS S3 API. Consequently, if your provider does not offer these values, it probably is not AWS S3 API compliant.

The `podcast` object:
- `category`: Follows the categories from Apple Podcasts (formerly iTunes Podcasts).
  A list can be found [here][itunes-categories].
- `language`: Has to be a language code out of [this list][rss-languages].


## Usage

The tool can be used in two modes, both on a command line:
- `interactive`
- `argument-based`

Before starting, create a new `virtualenv` with:
```sh
virtualenv -p python3.6 venv
```
and install the requirements:
```sh
venv/bin/pip3 install -r requirements.txt
```

The `interactive` mode is just triggered by normally executing the program and following the prompts:
```sh
venv/bin/python3 pycaster/pycaster.py
```

The `argument-based` accepts the following arguments:
```sh
venv/bin/python3 pycaster/pycaster.py \
    --title='Episode #1' \
    --description='Just a test' \
    --duration='160:55' \
    --file='./episode-1.mp3'
```

[gist-of-it]: https://gist.fm/
[itunes-categories]: https://castos.com/itunes-podcast-category-list/
[rss-languages]: http://www.rssboard.org/rss-language-codes
