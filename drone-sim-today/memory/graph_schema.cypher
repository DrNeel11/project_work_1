// Applied once via store.py's ensure_neo4j_schema(). Models the persistent
// "digital twin": a Defect identity that can be OBSERVED_IN many missions,
// LOCATED_ON a wall, and GREW_FROM its own earlier-mission observation
// (a temporal chain used to answer growth/change queries).
CREATE CONSTRAINT defect_id IF NOT EXISTS FOR (d:Defect) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT mission_id IF NOT EXISTS FOR (m:Mission) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT wall_name IF NOT EXISTS FOR (w:Wall) REQUIRE w.name IS UNIQUE;
