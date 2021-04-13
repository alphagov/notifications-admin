import json
import os
import pickle
import sqlite3
from pathlib import Path

rtree_index_path = Path(__file__).parent / 'rtree.pickle'
rtree_index = pickle.loads(rtree_index_path.read_bytes())


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
                name_singular TEXT NOT NULL,
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
                count_of_phones INTEGER,

                FOREIGN KEY (broadcast_area_library_id)
                    REFERENCES broadcast_area_libraries(id),

                FOREIGN KEY (broadcast_area_library_group_id)
                    REFERENCES broadcast_area_library_groups(id)
            )""")

            conn.execute("""
            CREATE TABLE broadcast_area_polygons (
                id TEXT PRIMARY KEY,
                polygons TEXT NOT NULL,
                simple_polygons TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_id
            ON broadcast_areas (broadcast_area_library_id);
            """)

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_group_id
            ON broadcast_areas (broadcast_area_library_group_id);
            """)

    def delete_library_data(self):
        # delete everything except broadcast_area_polygons
        with self.conn() as conn:
            conn.execute('DELETE FROM broadcast_area_libraries;')
            conn.execute('DELETE FROM broadcast_area_library_groups;')
            conn.execute('DELETE FROM broadcast_areas;')

    def insert_broadcast_area_library(self, id, *, name, name_singular, is_group):

        q = """
        INSERT INTO broadcast_area_libraries (id, name, name_singular, is_group)
        VALUES (?, ?, ?, ?)
        """

        with self.conn() as conn:
            conn.execute(q, (id, name, name_singular, is_group))

    def insert_broadcast_areas(self, areas, keep_old_features):

        areas_q = """
        INSERT INTO broadcast_areas (
            id, name,
            broadcast_area_library_id, broadcast_area_library_group_id,
            count_of_phones
        )
        VALUES (?, ?, ?, ?, ?)
        """

        features_q = """
        INSERT INTO broadcast_area_polygons (
            id,
            polygons, simple_polygons
        )
        VALUES (?, ?, ?)
        """

        with self.conn() as conn:
            for id, name, area_id, group, polygons, simple_polygons, count_of_phones in areas:
                conn.execute(areas_q, (
                    id, name, area_id, group, count_of_phones
                ))
                if not keep_old_features:
                    conn.execute(features_q, (
                        id, json.dumps(polygons), json.dumps(simple_polygons),
                    ))

    def query(self, sql, *args):
        with self.conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (*args,))
            return cursor.fetchall()

    def get_libraries(self):
        q = "SELECT id, name, name_singular, is_group FROM broadcast_area_libraries"
        results = self.query(q)
        libraries = [(row[0], row[1], row[2], row[3]) for row in results]
        return sorted(libraries)

    def get_areas(self, area_ids):
        q = """
        SELECT id, name, count_of_phones, broadcast_area_library_id
        FROM broadcast_areas
        WHERE id IN ({})
        """.format(("?," * len(area_ids))[:-1])

        results = self.query(q, *area_ids)

        areas = [
            (row[0], row[1], row[2], row[3])
            for row in results
        ]

        return areas

    def get_all_areas_for_library(self, library_id):
        is_multi_tier_library = self.query("""
        SELECT exists(
            SELECT 1
            FROM broadcast_areas
            WHERE broadcast_area_library_id = ? AND
            broadcast_area_library_group_id IS NOT NULL
        )
        """, library_id)[0][0]

        if is_multi_tier_library:
            # only interested in areas with children - eg local authorities, counties, unitary authorities. not wards.
            q = """
            SELECT id, name, count_of_phones, broadcast_area_library_id
            FROM broadcast_areas
            JOIN (
                SELECT DISTINCT broadcast_area_library_group_id
                FROM broadcast_areas
                WHERE broadcast_area_library_group_id IS NOT NULL
            ) AS parent_broadcast_areas ON parent_broadcast_areas.broadcast_area_library_group_id = broadcast_areas.id
            WHERE broadcast_area_library_id = ?
            """
        else:
            # Countries don't have any children, so the above query wouldn't return anything.
            q = """
            SELECT id, name, count_of_phones, broadcast_area_library_id
            FROM broadcast_areas
            WHERE broadcast_area_library_id = ?
            """

        results = self.query(q, library_id)

        return [
            (row[0], row[1], row[2], row[3])
            for row in results
        ]

    def get_all_areas_for_group(self, group_id):
        q = """
        SELECT id, name, count_of_phones, broadcast_area_library_id
        FROM broadcast_areas
        WHERE broadcast_area_library_group_id = ?
        """

        results = self.query(q, group_id)

        areas = [
            (row[0], row[1], row[2], row[3])
            for row in results
        ]

        return areas

    def get_parent_for_area(self, area_id):
        q = """
        SELECT id, name, count_of_phones, broadcast_area_library_id
        FROM broadcast_areas
        WHERE id IN (
            SELECT broadcast_area_library_group_id
            FROM broadcast_areas
            WHERE id = ?
        )
        """

        results = self.query(q, area_id)

        if not results:
            return None

        return (results[0][0], results[0][1], results[0][2], results[0][3])

    def get_polygons_for_area(self, area_id):
        q = """
        SELECT polygons
        FROM broadcast_area_polygons
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return json.loads(results[0][0])

    def get_simple_polygons_for_area(self, area_id):
        q = """
        SELECT simple_polygons
        FROM broadcast_area_polygons
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return json.loads(results[0][0])
