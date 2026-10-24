"""In-process drop-in for memory.store.MemoryStore (same public API and the same
matching rule), used to run the planner sweep on machines that cannot host the
PostgreSQL+pgvector and Neo4j containers (e.g. the rented GPU VM, which has no
Docker). The identity logic is a line-for-line port of match_or_create_defect:
among the 5 detections of the same class on the same wall nearest in cosine
distance of the appearance+spatial embedding (pgvector's `<=>`), the nearest one
whose defect lies within SPATIAL_MATCH_THRESH_M metres is the same defect.
Select it with UWTIG_MEMORY=inmem (see experiments/evaluate.py). The Neo4j
history graph is not needed by any planner or metric, so it is not mirrored.
"""
import numpy as np

from memory.store import SPATIAL_MATCH_THRESH_M, build_embedding


class InMemoryStore:
    def __init__(self):
        self.missions = {}      # id -> dict(scenario, planner, seed, mission_index)
        self.defects = {}       # id -> dict(...)
        self.detections = []    # dicts, in insertion order
        self._next = {"mission": 1, "defect": 1, "detection": 1}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def close(self):
        pass

    def create_mission(self, scenario, planner, seed, mission_index):
        mid = self._next["mission"]
        self._next["mission"] += 1
        self.missions[mid] = dict(scenario=scenario, planner=planner, seed=seed, mission_index=mission_index)
        return mid

    def match_or_create_defect(self, mission_id, wall, cls, confidence, uncertainty,
                                bbox, world_xyz, size_m, crop_bgr=None):
        world_xyz = tuple(float(v) for v in world_xyz)
        bbox = tuple(int(v) for v in bbox)
        confidence, uncertainty = float(confidence), float(uncertainty)
        size_m = float(size_m) if size_m is not None else None
        emb = build_embedding(cls, world_xyz, size_m, confidence, crop_bgr).astype(np.float64)

        rows = []
        for det in self.detections:
            d = self.defects[det["defect_id"]]
            if d["class"] != cls or d["wall"] != wall or d["status"] != "active":
                continue
            denom = np.linalg.norm(det["embedding"]) * np.linalg.norm(emb)
            dist = 1.0 - (float(det["embedding"] @ emb) / denom if denom > 0 else 0.0)
            rows.append((dist, det["defect_id"]))
        rows.sort(key=lambda r: r[0])
        candidates = [self.defects[did] for _, did in rows[:5]]

        best, best_dist = None, SPATIAL_MATCH_THRESH_M
        for d in candidates:
            dd = np.linalg.norm(np.array(d["xyz"]) - np.array(world_xyz))
            if dd < best_dist:
                best, best_dist = d, dd

        if best is not None:
            defect_id, is_new = best["id"], False
            growth_m = (size_m or 0.0) - (best["size_m"] or 0.0)
            best.update(last_seen_mission=mission_id, xyz=world_xyz, size_m=size_m)
        else:
            defect_id, is_new = self._next["defect"], True
            self._next["defect"] += 1
            self.defects[defect_id] = dict(id=defect_id, **{"class": cls}, wall=wall, status="active",
                                           first_seen_mission=mission_id, last_seen_mission=mission_id,
                                           xyz=world_xyz, size_m=size_m)
            growth_m = 0.0

        det_id = self._next["detection"]
        self._next["detection"] += 1
        self.detections.append(dict(id=det_id, mission_id=mission_id, defect_id=defect_id, wall=wall, **{"class": cls},
                                    confidence=confidence, uncertainty=uncertainty, bbox=bbox,
                                    world_x=world_xyz[0], world_y=world_xyz[1], world_z=world_xyz[2],
                                    size_m=size_m, embedding=emb))
        return det_id, defect_id, is_new, growth_m

    def get_defect_history(self, defect_id):
        hist = [dict(d, mission_index=self.missions[d["mission_id"]]["mission_index"])
                for d in self.detections if d["defect_id"] == defect_id]
        return sorted(hist, key=lambda r: r["mission_index"])

    def compute_growth(self, defect_id):
        history = self.get_defect_history(defect_id)
        if len(history) < 2:
            return 0.0
        return (history[-1]["size_m"] or 0.0) - (history[0]["size_m"] or 0.0)

    def active_defects_on_wall(self, wall):
        out = []
        for d in self.defects.values():
            if d["wall"] == wall and d["status"] == "active":
                out.append(dict(d, world_x=d["xyz"][0], world_y=d["xyz"][1], world_z=d["xyz"][2]))
        return out
