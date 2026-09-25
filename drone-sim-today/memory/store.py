"""Persistent defect memory: PostgreSQL+pgvector holds the append-only
detection log (with an appearance+spatial embedding used for nearest-neighbor
identity matching across missions), Neo4j holds the defect identity graph
((:Defect)-[:OBSERVED_IN]->(:Mission), (:Defect)-[:LOCATED_ON]->(:Wall),
(:Defect)-[:GREW_FROM]->(:Defect) temporal chain) used to answer
growth/history queries. This is the "digital twin" the proposal calls for.

Connects to the docker/docker-compose.yml services by default; override via
env vars (PG_HOST/PG_PORT/PG_DB/PG_USER/PG_PASSWORD, NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD).
"""
import os

import numpy as np
import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase

EMBED_DIM = 32
CLASS_LIST = ["crack", "corrosion", "leakage", "abscission", "bulge"]

PG_DSN = dict(
    host=os.environ.get("PG_HOST", "localhost"),
    port=int(os.environ.get("PG_PORT", 5433)),
    dbname=os.environ.get("PG_DB", "inspection"),
    user=os.environ.get("PG_USER", "inspection"),
    password=os.environ.get("PG_PASSWORD", "inspection_dev_only"),
)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "inspection_dev_only")

SPATIAL_MATCH_THRESH_M = 0.35


def build_embedding(cls, world_xyz, size_m, confidence, crop_bgr=None):
    """Appearance+spatial descriptor used for pgvector nearest-neighbor
    identity candidate retrieval (confirmed by a hard spatial gate in
    match_or_create_defect, so an imperfect embedding never wrongly merges
    two distinct real-world defects)."""
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    vec[0:3] = np.array(world_xyz) / 5.0
    if cls in CLASS_LIST:
        vec[3 + CLASS_LIST.index(cls)] = 1.0
    vec[8] = min(1.0, (size_m or 0.0) / 2.0)
    vec[9] = confidence
    if crop_bgr is not None and crop_bgr.size > 0:
        hsv = _bgr_to_hsv_hist(crop_bgr)
        vec[10:10 + len(hsv)] = hsv
    return vec


def _bgr_to_hsv_hist(crop_bgr):
    import cv2
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv], [0], None, [3], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], None, [3], [0, 256]).flatten()
    hist = np.concatenate([h_hist, s_hist])
    total = hist.sum()
    return hist / total if total > 0 else hist


class MemoryStore:
    def __init__(self):
        self.pg = psycopg2.connect(**PG_DSN)
        self.pg.autocommit = True
        self.neo4j = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.ensure_neo4j_schema()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.pg.close()
        self.neo4j.close()

    def ensure_neo4j_schema(self):
        stmts = [
            "CREATE CONSTRAINT defect_id IF NOT EXISTS FOR (d:Defect) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT mission_id IF NOT EXISTS FOR (m:Mission) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT wall_name IF NOT EXISTS FOR (w:Wall) REQUIRE w.name IS UNIQUE",
        ]
        with self.neo4j.session() as session:
            for stmt in stmts:
                session.run(stmt)

    # ---- missions ----
    def create_mission(self, scenario, planner, seed, mission_index):
        with self.pg.cursor() as cur:
            cur.execute(
                "INSERT INTO missions (scenario, planner, seed, mission_index) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                (scenario, planner, seed, mission_index),
            )
            mission_id = cur.fetchone()[0]
        with self.neo4j.session() as session:
            session.run(
                "MERGE (m:Mission {id: $id}) SET m.scenario=$scenario, m.planner=$planner, "
                "m.seed=$seed, m.mission_index=$idx",
                id=mission_id, scenario=scenario, planner=planner, seed=seed, idx=mission_index,
            )
        return mission_id

    # ---- detections + identity matching ----
    def match_or_create_defect(self, mission_id, wall, cls, confidence, uncertainty,
                                bbox, world_xyz, size_m, crop_bgr=None):
        """Records a detection and resolves it to a persistent defect
        identity: nearest-neighbor candidates via pgvector cosine distance,
        confirmed by a hard spatial(+class) gate; else a new identity is
        created. Returns (detection_id, defect_id, is_new, growth_m)."""
        world_xyz = tuple(float(v) for v in world_xyz)
        bbox = tuple(int(v) for v in bbox)
        confidence, uncertainty = float(confidence), float(uncertainty)
        size_m = float(size_m) if size_m is not None else None
        embedding = build_embedding(cls, world_xyz, size_m, confidence, crop_bgr)

        defect_id, growth_m, is_new = None, None, True
        with self.pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT d.id, d.world_x, d.world_y, d.world_z, d.size_m
                FROM defects d
                JOIN detections det ON det.defect_id = d.id
                WHERE d.class = %s AND d.wall = %s AND d.status = 'active'
                ORDER BY det.embedding <=> %s::vector
                LIMIT 5
                """,
                (cls, wall, [float(x) for x in embedding]),
            )
            candidates = cur.fetchall()

        best, best_dist = None, SPATIAL_MATCH_THRESH_M
        for row in candidates:
            d = np.linalg.norm(np.array([row["world_x"], row["world_y"], row["world_z"]]) - np.array(world_xyz))
            if d < best_dist:
                best, best_dist = row, d

        if best is not None:
            defect_id = best["id"]
            is_new = False
            prev_size = best["size_m"] or 0.0
            growth_m = (size_m or 0.0) - prev_size
            with self.pg.cursor() as cur:
                cur.execute(
                    "UPDATE defects SET last_seen_mission=%s, world_x=%s, world_y=%s, world_z=%s, "
                    "size_m=%s WHERE id=%s",
                    (mission_id, *world_xyz, size_m, defect_id),
                )
        else:
            with self.pg.cursor() as cur:
                cur.execute(
                    "INSERT INTO defects (class, wall, first_seen_mission, last_seen_mission, "
                    "world_x, world_y, world_z, size_m) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (cls, wall, mission_id, mission_id, *world_xyz, size_m),
                )
                defect_id = cur.fetchone()[0]
            growth_m = 0.0

        with self.pg.cursor() as cur:
            cur.execute(
                "INSERT INTO detections (mission_id, defect_id, wall, class, confidence, uncertainty, "
                "bbox_x, bbox_y, bbox_w, bbox_h, world_x, world_y, world_z, size_m, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (mission_id, defect_id, wall, cls, confidence, uncertainty,
                 *bbox, *world_xyz, size_m, [float(x) for x in embedding]),
            )
            detection_id = cur.fetchone()[0]

        self._sync_neo4j(defect_id, mission_id, wall, cls, is_new, growth_m)
        return detection_id, defect_id, is_new, growth_m

    def _sync_neo4j(self, defect_id, mission_id, wall, cls, is_new, growth_m):
        with self.neo4j.session() as session:
            session.run(
                "MERGE (w:Wall {name: $wall}) "
                "MERGE (d:Defect {id: $id}) SET d.class=$cls "
                "MERGE (d)-[:LOCATED_ON]->(w) "
                "WITH d "
                "MATCH (m:Mission {id: $mission_id}) "  # created by create_mission() before any detection
                "MERGE (d)-[r:OBSERVED_IN]->(m) SET r.growth_m=$growth_m",
                id=defect_id, cls=cls, wall=wall, mission_id=mission_id, growth_m=growth_m,
            )
            if not is_new:
                session.run(
                    """
                    MATCH (d:Defect {id: $id})-[:OBSERVED_IN]->(m:Mission)
                    WHERE m.id < $mission_id
                    WITH d, m ORDER BY m.mission_index DESC LIMIT 1
                    MATCH (m)<-[r:OBSERVED_IN]-(d)
                    SET r.grew_from_prior = true
                    """,
                    id=defect_id, mission_id=mission_id,
                )

    def get_defect_history(self, defect_id):
        with self.pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT det.*, m.mission_index FROM detections det "
                "JOIN missions m ON m.id = det.mission_id "
                "WHERE det.defect_id = %s ORDER BY m.mission_index",
                (defect_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def compute_growth(self, defect_id):
        history = self.get_defect_history(defect_id)
        if len(history) < 2:
            return 0.0
        return (history[-1]["size_m"] or 0.0) - (history[0]["size_m"] or 0.0)

    def active_defects_on_wall(self, wall):
        with self.pg.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM defects WHERE wall=%s AND status='active'", (wall,))
            return [dict(r) for r in cur.fetchall()]
