import sqlite3


class Episode:
    def __init__(self, title, description, file_uri, file_type, file_size, db_id=None):
        self.db_id = db_id
        self.title = title
        self.description = description
        self.file_uri = file_uri
        self.file_type = file_type
        self.file_size = file_size


class Database:
    def __init__(self, db_file):
        self.db = self.init_db(db_file)

    def create_episode_database(self):
        cursor = self._get_cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT unique,
                description TEXT,
                file_uri TEXT unique,
                file_type TEXT,
                file_size TEXT
            )
            '''
        )
        self._commit_db()
        cursor.close()

    def insert_new_episode(self, episode: Episode):
        cursor = self._get_cursor()
        cursor.execute(
            '''
            INSERT INTO episodes(title, description, file_uri, file_type, file_size)
            VALUES(:title, :description, :file_uri, :file_type, :file_size)
            ''',
            {
                'title': episode.title,
                'description': episode.description,
                'file_uri': episode.file_uri,
                'file_type': episode.file_type,
                'file_size': episode.file_size,
            }
        )
        self._commit_db()
        cursor.close()

    def retrieve_all_episodes(self):
        cursor = self._get_cursor()
        cursor.execute(
            '''
            SELECT * FROM episodes
            '''
        )
        self._commit_db()
        rows = cursor.fetchall()
        cursor.close()
        return self._deserialize_episodes(rows)

    def _deserialize_episodes(self, episode_rows):
        episodes = []

        for row in episode_rows:
            episodes.append(self._deserialize_episode(row))

        return episodes

    def _get_cursor(self):
        return self.db.cursor()

    def _commit_db(self):
        return self.db.commit()

    @staticmethod
    def _deserialize_episode(episode_row):
        return Episode(
            db_id=episode_row[0],
            title=episode_row[1],
            description=episode_row[2],
            file_uri=episode_row[3],
            file_type=episode_row[4],
            file_size=episode_row[5],
        )

    @staticmethod
    def init_db(db_file):
        return sqlite3.connect(db_file)
