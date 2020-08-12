import os
import sqlite3
from pathlib import Path

import geojson


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
                name TEXT NOT NULL,
                is_group BOOLEAN NOT NULL
            )""")

            conn.execute("""
            CREATE TABLE broadcast_area_library_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                broadcast_area_library_id TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE TABLE broadcast_areas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                broadcast_area_library_id TEXT NOT NULL,
                broadcast_area_library_group_id TEXT,

                FOREIGN KEY (broadcast_area_library_id)
                    REFERENCES broadcast_area_libraries(id),

                FOREIGN KEY (broadcast_area_library_group_id)
                    REFERENCES broadcast_area_library_groups(id)
            )""")

            conn.execute("""
            CREATE TABLE broadcast_area_features (
                id TEXT PRIMARY KEY,
                feature_geojson TEXT NOT NULL,
                simple_feature_geojson TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_id
            ON broadcast_areas (broadcast_area_library_id);
            """)

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_group_id
            ON broadcast_areas (broadcast_area_library_group_id);
            """)

    def insert_broadcast_area_library(self, id, name, is_group):

        q = """
        INSERT INTO broadcast_area_libraries (id, name, is_group)
        VALUES (?, ?, ?)
        """

        with self.conn() as conn:
            conn.execute(q, (id, name, is_group))

    def insert_broadcast_areas(self, areas):

        areas_q = """
        INSERT INTO broadcast_areas (
            id, name,
            broadcast_area_library_id, broadcast_area_library_group_id
        )
        VALUES (?, ?, ?, ?)
        """

        features_q = """
        INSERT INTO broadcast_area_features (
            id,
            feature_geojson, simple_feature_geojson
        )
        VALUES (?, ?, ?)
        """

        with self.conn() as conn:
            for id, name, area_id, group, feature, simple_feature in areas:
                conn.execute(areas_q, (
                    id, name, area_id, group,
                ))
                conn.execute(features_q, (
                    id, geojson.dumps(feature), geojson.dumps(simple_feature),
                ))

    def query(self, sql, *args):
        with self.conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (*args,))
            return cursor.fetchall()

    def get_libraries(self):
        q = "SELECT id, name, is_group FROM broadcast_area_libraries"
        results = self.query(q)
        libraries = [(row[0], row[1], row[2]) for row in results]
        return sorted(libraries)

    def get_library_description(self, library_id):
        q = """
        WITH
        areas AS (
            SELECT * FROM broadcast_areas
            WHERE broadcast_area_library_id = ?
            AND broadcast_area_library_group_id IS NULL
        ),
        area_count AS (SELECT COUNT(*) AS c FROM areas),
        subset_area_count AS (SELECT c - 4 FROM area_count),
        description_area_names  AS (SELECT name FROM areas ORDER BY name ASC LIMIT 4),
        description_areas_joined AS (
            SELECT GROUP_CONCAT(name, ", ") FROM description_area_names
        )
        SELECT
        CASE (SELECT * FROM subset_area_count)
        WHEN 0 THEN
            (SELECT * FROM description_areas_joined)
        ELSE
            (SELECT * FROM description_areas_joined)
            || ", and "
            || (SELECT * FROM subset_area_count)
            || " more…"
        END
        """
        description = self.query(q, library_id)[0][0]
        return description

    def get_areas(self, area_ids):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE id IN ({})
        """.format(("?," * len(area_ids))[:-1])

        results = self.query(q, *area_ids)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_all_areas_for_library(self, library_id):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE broadcast_area_library_id = ?
        AND broadcast_area_library_group_id IS NULL
        """

        results = self.query(q, library_id)

        return [
            (row[0], row[1])
            for row in results
        ]

    def get_all_areas_for_group(self, group_id):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE broadcast_area_library_group_id = ?
        """

        results = self.query(q, group_id)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_all_groups_for_library(self, library_id):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE broadcast_area_library_group_id = NULL
        AND broadcast_area_library_id = ?
        """

        results = self.query(q, library_id)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_feature_for_area(self, area_id):
        q = """
        SELECT feature_geojson
        FROM broadcast_area_features
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return results[0][0]

    def get_simple_feature_for_area(self, area_id):
        q = """
        SELECT simple_feature_geojson
        FROM broadcast_area_features
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return results[0][0]
