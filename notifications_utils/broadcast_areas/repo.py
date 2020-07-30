import os
from pathlib import Path
import sqlite3

from notifications_utils.safe_string import make_string_safe_for_id


class BroadcastAreasRepository(object):
    def __init__(self):
        self.database = Path(__file__).resolve().parent / 'broadcast-areas.sqlite3'

    def conn(self):
        return sqlite3.connect(str(self.database))

    def delete_db(self):
        os.remove(str(self.database))

    def create_tables(self):
        with self.conn() as conn:
            conn.execute("""
            CREATE TABLE broadcast_area_libraries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE TABLE broadcast_areas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                broadcast_area_library_id TEXT NOT NULL,
                feature_geojson TEXT NOT NULL,
                simple_feature_geojson TEXT NOT NULL,

                FOREIGN KEY (broadcast_area_library_id)
                    REFERENCES broadcast_area_libraries(id)
            )""")

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_id
            ON broadcast_areas (broadcast_area_library_id);
            """)

    def insert_broadcast_area_library(self, broadcast_area_name):
        broadcast_area_id = make_string_safe_for_id(broadcast_area_name)

        q = """
        INSERT INTO broadcast_area_libraries (id, name)
        VALUES (?, ?)
        """

        with self.conn() as conn:
            conn.execute(q, (broadcast_area_id, broadcast_area_name))

    def insert_broadcast_areas(self, areas):

        q = """
        INSERT INTO broadcast_areas (
            id, name,
            broadcast_area_library_id, feature_geojson, simple_feature_geojson
        )
        VALUES (?, ?, ?, ?, ?)
        """

        with self.conn() as conn:
            for name, area_name, feature, simple_feature in areas:
                id = make_string_safe_for_id(name)
                area_id = make_string_safe_for_id(area_name)

                conn.execute(q, (
                    id, name, area_id,
                    geojson.dumps(feature),
                    geojson.dumps(simple_feature),
                ))

    def query(self, sql, *args):
        with self.conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (*args,))
            return cursor.fetchall()

    def get_libraries(self):
        q = "SELECT id, name FROM broadcast_area_libraries"
        results = self.query(q)
        libraries = [row[1] for row in results]
        return sorted(libraries)

    def get_library_description(self, library_id):
        q = """
        WITH
        areas AS (SELECT * FROM broadcast_areas
                  WHERE broadcast_area_library_id = ?),
        area_count AS (SELECT COUNT(*) AS c FROM areas),
        subset_area_count AS (SELECT c - 4 FROM area_count),
        some_area_names  AS (SELECT name FROM areas LIMIT 100),
        some_shuffled_area_names AS (
            SELECT name FROM some_area_names ORDER BY RANDOM()
        ),
        description_area_names AS (
            SELECT name FROM some_shuffled_area_names LIMIT 4
        ),
        description_areas_joined AS (
            SELECT GROUP_CONCAT(name, ", ") FROM description_area_names
        )
        SELECT
        CASE (SELECT * FROM subset_area_count)
        WHEN 0 THEN
            (SELECT * FROM description_areas_joined)
        ELSE
            (SELECT * FROM description_areas_joined)
            || ", "
            || (SELECT * FROM subset_area_count)
            || " more…"
        END
        """
        description = self.query(q, library_id)[0][0]
        return description

    def get_areas(self, *area_ids):
        with self.conn() as conn:
            cursor = conn.cursor()

            q = """
            SELECT id, name, feature_geojson, simple_feature_geojson
            FROM broadcast_areas
            WHERE id IN ({})
            """.format(("?," * len(*area_ids))[:-1])
            cursor.execute(q, *area_ids)
            results = cursor.fetchall()

            areas = [
                (row[0], row[1], row[2], row[3])
                for row in results
            ]

            return areas

    def get_all_areas_for_library(self, library_id):
        q = """
        SELECT id, name, feature_geojson, simple_feature_geojson
        FROM broadcast_areas
        WHERE broadcast_area_library_id = ?
        """

        results = self.query(q, library_id)

        areas = [
            (row[0], row[1], row[2], row[3])
            for row in results
        ]

        return areas
