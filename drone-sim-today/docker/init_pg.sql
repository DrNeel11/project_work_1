CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS missions (
    id SERIAL PRIMARY KEY,
    scenario TEXT NOT NULL,
    planner TEXT NOT NULL,
    seed INT NOT NULL,
    mission_index INT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS defects (
    id SERIAL PRIMARY KEY,
    neo4j_id TEXT UNIQUE,          -- mirrors the Neo4j (:Defect) node id for this identity
    class TEXT NOT NULL,
    wall TEXT NOT NULL,
    first_seen_mission INT NOT NULL REFERENCES missions(id),
    last_seen_mission INT NOT NULL REFERENCES missions(id),
    world_x REAL NOT NULL,
    world_y REAL NOT NULL,
    world_z REAL NOT NULL,
    size_m REAL,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    mission_id INT NOT NULL REFERENCES missions(id),
    defect_id INT REFERENCES defects(id),
    wall TEXT NOT NULL,
    class TEXT NOT NULL,
    confidence REAL NOT NULL,
    uncertainty REAL NOT NULL,
    bbox_x INT, bbox_y INT, bbox_w INT, bbox_h INT,
    world_x REAL, world_y REAL, world_z REAL,
    size_m REAL,
    embedding vector(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No ivfflat index: dataset scale here is small enough that brute-force
-- cosine distance (embedding <=> query) via store.py is fast without one,
-- and ivfflat requires populated data to build well.
CREATE INDEX IF NOT EXISTS detections_defect_idx ON detections (defect_id);
CREATE INDEX IF NOT EXISTS detections_mission_idx ON detections (mission_id);
