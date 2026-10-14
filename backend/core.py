"""Local research store. Half-open millisecond intervals, stable UUID identities."""

import json, math, sqlite3, uuid, datetime
from xml.etree import ElementTree as ET


class ValidationError(ValueError):
    pass


def uid():
    return "id_" + uuid.uuid4().hex


def validate_interval(start, end, duration):
    if (
        type(start) is not int
        or type(end) is not int
        or not 0 <= start < end <= duration
    ):
        raise ValidationError(
            "Interval must use integer milliseconds: 0 ≤ start < end ≤ duration"
        )


def validate_pose(pose, duration):
    if (
        not isinstance(pose, dict)
        or not isinstance(pose.get("model"), dict)
        or not isinstance(pose.get("topology"), dict)
        or not isinstance(pose.get("frames"), list)
    ):
        raise ValidationError("Pose must include model, topology and frames")
    if not isinstance(pose["model"].get("name"), str) or not isinstance(
        pose["model"].get("version"), str
    ):
        raise ValidationError("Model name and version must be strings")
    if not isinstance(pose["topology"].get("version"), str):
        raise ValidationError("Topology version required")
    if pose.get("coordinateSystem") != "normalized-image-2d":
        raise ValidationError("Only normalized-image-2d is supported; no calibrated 3D")
    if not pose.get("model") or not pose.get("topology"):
        raise ValidationError("Pose model and topology are required")
    names = pose["topology"].get("names", [])
    if not names or len(names) != len(set(names)):
        raise ValidationError("Unique topology names required")
    transforms = pose.get("transforms", {})
    if (
        type(transforms.get("offsetMs", 0)) is not int
        or type(transforms.get("mirrored", False)) is not bool
    ):
        raise ValidationError(
            "Transforms require integer offsetMs and boolean mirrored"
        )
    previous = -1
    for frame in pose.get("frames", []):
        t = frame.get("timeMs")
        if type(t) is not int or not previous < t <= duration:
            raise ValidationError("Pose timestamps must increase in milliseconds")
        previous = t
        for key, p in frame.get("points", {}).items():
            if (
                key not in names
                or len(p) != 2
                or any(
                    type(v) not in (int, float)
                    or not math.isfinite(v)
                    or not 0 <= v <= 1
                    for v in p
                )
            ):
                raise ValidationError("Invalid 2D landmark")
    if any(n not in names for n in pose["topology"].get("motionPoints", [])):
        raise ValidationError("Unknown motion point")
    for edge in pose["topology"].get("edges", []):
        if len(edge) != 2 or any(n not in names for n in edge):
            raise ValidationError("Invalid topology edge")


def nearest_frame(pose, time_ms, tolerance=150):
    frames = pose.get("frames", [])
    if not frames:
        return None
    f = min(frames, key=lambda f: abs(f["timeMs"] - time_ms))
    return f if abs(f["timeMs"] - time_ms) <= tolerance else None


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT, duration INTEGER, pose TEXT, source_eaf TEXT);
        CREATE TABLE IF NOT EXISTS tiers(id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id), name TEXT, channel TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS lexicon(id TEXT PRIMARY KEY, gloss TEXT, description TEXT);
        CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY, tier_id TEXT REFERENCES tiers(id), start INTEGER, end INTEGER, value TEXT, lexicon_id TEXT REFERENCES lexicon(id), provenance TEXT, start_slot TEXT, end_slot TEXT);
        CREATE INDEX IF NOT EXISTS annotation_time ON annotations(tier_id,start,end);
        CREATE TABLE IF NOT EXISTS suggestions(id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id), tier_id TEXT REFERENCES tiers(id), start INTEGER, end INTEGER, value TEXT, status TEXT, provenance TEXT, annotation_id TEXT);
        """)
        self.db.commit()

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def snapshot(self, pid):
        p = self.rows("SELECT * FROM projects WHERE id=?", (pid,))
        if not p:
            raise ValidationError("Unknown project")
        p = p[0]
        p["pose"] = json.loads(p["pose"])
        source = p.pop("source_eaf")
        p["mediaDescriptors"] = (
            [
                dict(n.attrib)
                for n in ET.fromstring(source).findall("./HEADER/MEDIA_DESCRIPTOR")
            ]
            if source
            else []
        )
        p["tiers"] = self.rows("SELECT * FROM tiers WHERE project_id=?", (pid,))
        p["annotations"] = self.rows(
            "SELECT a.* FROM annotations a JOIN tiers t ON t.id=a.tier_id WHERE t.project_id=? ORDER BY start",
            (pid,),
        )
        p["lexicon"] = self.rows("SELECT * FROM lexicon")
        p["suggestions"] = self.rows(
            "SELECT * FROM suggestions WHERE project_id=?", (pid,)
        )
        for a in p["annotations"] + p["suggestions"]:
            a["provenance"] = json.loads(a["provenance"] or "{}")
        return p

    def demo(self):
        if self.rows("SELECT id FROM projects"):
            return self.rows("SELECT id FROM projects")[0]["id"]
        pid = uid()
        duration = 8000
        names = [
            "head",
            "leftShoulder",
            "rightShoulder",
            "leftElbow",
            "rightElbow",
            "leftWrist",
            "rightWrist",
            "hip",
        ]
        frames = []
        for t in range(0, duration + 1, 100):
            wave = math.sin(t / 350) * 0.12 if 1200 < t < 3100 or 4500 < t < 6500 else 0
            frames.append(
                {
                    "timeMs": t,
                    "points": {
                        "head": [0.5, 0.19],
                        "leftShoulder": [0.38, 0.34],
                        "rightShoulder": [0.62, 0.34],
                        "leftElbow": [0.3, 0.52],
                        "rightElbow": [0.7, 0.52],
                        "leftWrist": [0.34, 0.65],
                        "rightWrist": [0.68 + wave, 0.45 + wave],
                        "hip": [0.5, 0.8],
                    },
                }
            )
        pose = {
            "coordinateSystem": "normalized-image-2d",
            "model": {
                "name": "synthetic-stick-figure",
                "version": "1",
                "trained": False,
            },
            "topology": {
                "version": "synthetic-8-v1",
                "names": names,
                "motionPoints": ["leftWrist", "rightWrist"],
                "edges": [
                    ["head", "leftShoulder"],
                    ["head", "rightShoulder"],
                    ["leftShoulder", "leftElbow"],
                    ["leftElbow", "leftWrist"],
                    ["rightShoulder", "rightElbow"],
                    ["rightElbow", "rightWrist"],
                    ["leftShoulder", "hip"],
                    ["rightShoulder", "hip"],
                ],
            },
            "transforms": {"mirrored": False, "offsetMs": 0},
            "frames": frames,
        }
        self.db.execute(
            "INSERT INTO projects VALUES(?,?,?,?,?)",
            (
                pid,
                "合成動作研究 / Synthetic motion study",
                duration,
                json.dumps(pose),
                None,
            ),
        )
        templates = [
            ("慣用手 / Dominant hand", "dominant", "#3dd6bd"),
            ("非慣用手 / Non-dominant hand", "non-dominant", "#7aabff"),
            ("眉毛 / Brows", "brows", "#cf91ff"),
            ("頭部 / Head", "head", "#ffa96a"),
            ("口部 / Mouth", "mouth", "#f1ce72"),
            ("動作提案 / Motion candidates", "motion", "#a8cbaa"),
        ]
        tids = []
        for name, ch, color in templates:
            tid = uid()
            tids.append(tid)
            self.db.execute(
                "INSERT INTO tiers VALUES(?,?,?,?,?)", (tid, pid, name, ch, color)
            )
        lid = uid()
        self.db.execute(
            "INSERT INTO lexicon VALUES(?,?,?)",
            (
                lid,
                "DEMO-MOTION",
                "合成示例；不是臺灣手語詞彙 / Synthetic example, not a TSL sign",
            ),
        )
        self.db.commit()
        self.save_annotation(
            pid,
            {
                "tier_id": tids[0],
                "start": 1200,
                "end": 3100,
                "value": "DEMO-MOTION",
                "lexicon_id": lid,
            },
        )
        self.save_annotation(
            pid,
            {
                "tier_id": tids[2],
                "start": 1600,
                "end": 2800,
                "value": "示例抬眉 / Demo brow raise",
            },
        )
        return pid

    def create_project(self, name, duration):
        if type(duration) is not int or not 1 <= duration <= 86_400_000:
            raise ValidationError(
                "Duration must be integer milliseconds, up to 24 hours"
            )
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Project name required")
        pid = uid()
        pose = {
            "coordinateSystem": "normalized-image-2d",
            "model": {"name": "none", "version": "1"},
            "topology": {"version": "empty-v1", "names": ["placeholder"], "edges": []},
            "transforms": {"offsetMs": 0, "mirrored": False},
            "frames": [],
        }
        with self.db:
            self.db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?)",
                (pid, name, duration, json.dumps(pose), None),
            )
            for title, channel, color in [
                ("慣用手 / Dominant hand", "dominant", "#3dd6bd"),
                ("非慣用手 / Non-dominant hand", "non-dominant", "#7aabff"),
                ("眉毛 / Brows", "brows", "#cf91ff"),
                ("頭部 / Head", "head", "#ffa96a"),
                ("口部 / Mouth", "mouth", "#f1ce72"),
                ("動作提案 / Motion candidates", "motion", "#a8cbaa"),
            ]:
                self.db.execute(
                    "INSERT INTO tiers VALUES(?,?,?,?,?)",
                    (uid(), pid, title, channel, color),
                )
        return pid

    def save_annotation(self, pid, a, _commit=True):
        p = self.snapshot(pid)
        tid = a["tier_id"]
        if tid not in [t["id"] for t in p["tiers"]]:
            raise ValidationError("Unknown tier")
        validate_interval(a["start"], a["end"], p["duration"])
        aid = a.get("id") or uid()
        old = self.rows("SELECT * FROM annotations WHERE id=?", (aid,))
        if old and old[0]["tier_id"] not in [t["id"] for t in p["tiers"]]:
            raise ValidationError("Annotation belongs to another project")
        if self.rows(
            "SELECT id FROM annotations WHERE tier_id=? AND start<? AND end>? AND id<>?",
            (tid, a["end"], a["start"], aid),
        ):
            raise ValidationError("Same-tier overlap is not allowed; use another tier")
        if not isinstance(a.get("value", ""), str) or len(a.get("value", "")) > 2000:
            raise ValidationError("Annotation must be text up to 2000 characters")
        lid = a.get("lexicon_id") or None
        if lid and not self.rows("SELECT id FROM lexicon WHERE id=?", (lid,)):
            raise ValidationError("Unknown lexicon ID")
        slots = (old[0]["start_slot"], old[0]["end_slot"]) if old else (uid(), uid())
        self.db.execute(
            "INSERT OR REPLACE INTO annotations VALUES(?,?,?,?,?,?,?,?,?)",
            (
                aid,
                tid,
                a["start"],
                a["end"],
                a.get("value", ""),
                lid,
                json.dumps(
                    a.get(
                        "provenance",
                        old
                        and json.loads(old[0]["provenance"])
                        or {"source": "manual"},
                    )
                ),
                *slots,
            ),
        )
        if _commit:
            self.db.commit()
        return aid

    def overlap(self, pid, start, end, channels=None):
        validate_interval(start, end, self.snapshot(pid)["duration"])
        result = self.rows(
            "SELECT a.*,t.name tier_name,t.channel FROM annotations a JOIN tiers t ON t.id=a.tier_id WHERE t.project_id=? AND a.start<? AND a.end>? ORDER BY a.start",
            (pid, end, start),
        )
        return [a for a in result if not channels or a["channel"] in channels]

    def lexicon(self, data):
        lid = data.get("id") or uid()
        if not data.get("gloss", "").strip():
            raise ValidationError("Gloss required")
        self.db.execute(
            "INSERT INTO lexicon VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET gloss=excluded.gloss,description=excluded.description",
            (lid, data["gloss"], data.get("description", "")),
        )
        self.db.commit()
        return lid

    def propose(self, pid):
        p = self.snapshot(pid)
        pose = p["pose"]
        tid = next((t["id"] for t in p["tiers"] if t["channel"] == "motion"), None)
        if not tid:
            raise ValidationError("A motion candidate tier is required")
        intervals = []
        start = None
        last = None
        for before, after in zip(pose["frames"], pose["frames"][1:]):
            dt = (after["timeMs"] - before["timeMs"]) / 1000
            pairs = [
                (before["points"][k], after["points"][k])
                for k in before["points"].keys() & after["points"].keys()
                if k in pose["topology"].get("motionPoints", []) or "wrist" in k.lower()
            ]
            speed = max((math.dist(a, b) / dt for a, b in pairs), default=0)
            active = bool(pairs) and speed > 0.12 and dt <= 0.25
            if active and start is None:
                start = before["timeMs"]
            if not active and start is not None:
                if before["timeMs"] - start >= 300:
                    intervals.append((start, before["timeMs"]))
                start = None
            last = after["timeMs"]
        if start is not None and last - start >= 300:
            intervals.append((start, last))
        for start, end in intervals:
            offset = pose.get("transforms", {}).get("offsetMs", 0)
            start += offset
            end += offset
            if not 0 <= start < end <= p["duration"]:
                continue
            if self.rows(
                "SELECT id FROM suggestions WHERE project_id=? AND start=? AND end=?",
                (pid, start, end),
            ):
                continue
            provenance = {
                "provider": "motion-boundary-v1",
                "kind": "heuristic",
                "thresholdNormalizedPerSecond": 0.12,
                "minimumDurationMs": 300,
                "model": pose["model"],
                "topology": pose["topology"]["version"],
                "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "warning": "Candidate motion interval; not linguistic segmentation or sign recognition",
            }
            self.db.execute(
                "INSERT INTO suggestions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    uid(),
                    pid,
                    tid,
                    start,
                    end,
                    "待標記動作 / Unlabelled motion",
                    "pending",
                    json.dumps(provenance),
                    None,
                ),
            )
        self.db.commit()

    def review(self, pid, sid, decision, edits=None):
        s = self.rows(
            "SELECT * FROM suggestions WHERE id=? AND project_id=?", (sid, pid)
        )
        if not s:
            raise ValidationError("Unknown suggestion")
        s = s[0]
        if decision == "undo":
            if s["status"] == "pending":
                raise ValidationError("Nothing to undo")
            if s["annotation_id"]:
                self.db.execute(
                    "DELETE FROM annotations WHERE id=?", (s["annotation_id"],)
                )
            self.db.execute(
                'UPDATE suggestions SET status="pending",annotation_id=NULL WHERE id=?',
                (sid,),
            )
        elif decision in ("accepted", "rejected"):
            if s["status"] != "pending":
                raise ValidationError("Already reviewed; undo first")
            aid = None
            if decision == "accepted":
                data = {
                    "tier_id": s["tier_id"],
                    "start": s["start"],
                    "end": s["end"],
                    "value": s["value"],
                    **(edits or {}),
                    "provenance": {
                        **json.loads(s["provenance"]),
                        "suggestionId": sid,
                        "review": "accepted",
                        "originalInterval": [s["start"], s["end"]],
                    },
                }
                aid = self.save_annotation(pid, data, _commit=False)
            provenance = json.loads(s["provenance"])
            provenance["lastReview"] = {
                "decision": decision,
                "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            self.db.execute(
                "UPDATE suggestions SET status=?,annotation_id=?,provenance=? WHERE id=?",
                (decision, aid, json.dumps(provenance), sid),
            )
        else:
            raise ValidationError("Invalid review decision")
        self.db.commit()
