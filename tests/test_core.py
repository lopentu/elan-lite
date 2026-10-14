import tempfile, unittest, json
from pathlib import Path
from backend.core import Store, ValidationError, validate_pose, nearest_frame
from backend.eaf import import_eaf, export_eaf, parse_eaf

EAF = """<ANNOTATION_DOCUMENT AUTHOR="研究者" DATE="2026-10-14T00:00:00Z" VERSION="3.0" FORMAT="3.0"><HEADER TIME_UNITS="milliseconds"><MEDIA_DESCRIPTOR MEDIA_URL="file:///local/demo.mp4" RELATIVE_MEDIA_URL="./demo.mp4" MIME_TYPE="video/mp4" TIME_ORIGIN="125"/><PROPERTY NAME="note">臺灣 &amp; gestures</PROPERTY></HEADER><TIME_ORDER><TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="100"/><TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="900"/><TIME_SLOT TIME_SLOT_ID="ts3" TIME_VALUE="100"/><TIME_SLOT TIME_SLOT_ID="ts4" TIME_VALUE="900"/></TIME_ORDER><TIER TIER_ID="慣用手" LINGUISTIC_TYPE_REF="independent"><ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="ts2"><ANNOTATION_VALUE>你好 &amp; demo</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION></TIER><TIER TIER_ID="眉毛" LINGUISTIC_TYPE_REF="independent"><ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a2" TIME_SLOT_REF1="ts3" TIME_SLOT_REF2="ts4"><ANNOTATION_VALUE>示例</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION></TIER><LINGUISTIC_TYPE LINGUISTIC_TYPE_ID="independent" TIME_ALIGNABLE="true" GRAPHIC_REFERENCES="false"/></ANNOTATION_DOCUMENT>"""


class ResearchWorkflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.sqlite"
        self.s = Store(self.path)
        self.pid = self.s.demo()
        self.p = self.s.snapshot(self.pid)

    def tearDown(self):
        self.s.db.close()
        self.tmp.cleanup()

    def test_edit_persistence(self):
        a = self.p["annotations"][0]
        a.update(start=1300, end=3000, value="臺灣手語研究")
        self.s.save_annotation(self.pid, a)
        other = Store(self.path)
        saved = next(
            x for x in other.snapshot(self.pid)["annotations"] if x["id"] == a["id"]
        )
        self.assertEqual(saved["value"], "臺灣手語研究")
        self.assertEqual(saved["start"], 1300)
        other.db.close()

    def test_stable_lexicon_rename(self):
        l = self.p["lexicon"][0]
        l["gloss"] = "renamed"
        self.s.lexicon(l)
        p = self.s.snapshot(self.pid)
        self.assertEqual(p["annotations"][0]["lexicon_id"], l["id"])
        self.assertEqual(p["lexicon"][0]["gloss"], "renamed")

    def test_overlap_half_open_cross_tier(self):
        self.assertEqual(len(self.s.overlap(self.pid, 1700, 2000)), 2)
        self.assertEqual(len(self.s.overlap(self.pid, 3100, 3200)), 0)
        self.assertEqual(len(self.s.overlap(self.pid, 1700, 2000, ["brows"])), 1)

    def test_create_project(self):
        pid = self.s.create_project("新研究", 120000)
        p = self.s.snapshot(pid)
        self.assertEqual(p["duration"], 120000)
        self.assertEqual(len(p["tiers"]), 6)
        self.assertFalse(p["annotations"])
        self.assertFalse(p["pose"]["frames"])

    def test_invalid_intervals(self):
        a = self.p["annotations"][0]
        for start, end in [(100, 100), (-1, 500), (0, 9000), (0.1, 500)]:
            with self.assertRaises(ValidationError):
                self.s.save_annotation(self.pid, {**a, "start": start, "end": end})
        with self.assertRaises(ValidationError):
            self.s.save_annotation(
                self.pid, {**a, "id": None, "start": 1300, "end": 2900}
            )

    def test_review_and_undo(self):
        self.s.propose(self.pid)
        s = self.s.snapshot(self.pid)["suggestions"][0]
        self.s.review(self.pid, s["id"], "accepted", {"value": "reviewed"})
        p = self.s.snapshot(self.pid)
        a = next(
            a
            for a in p["annotations"]
            if a["provenance"].get("suggestionId") == s["id"]
        )
        self.assertEqual(a["value"], "reviewed")
        self.assertEqual(a["provenance"]["kind"], "heuristic")
        with self.assertRaises(ValidationError):
            self.s.review(self.pid, s["id"], "accepted")
        self.s.review(self.pid, s["id"], "undo")
        self.assertFalse(
            any(
                a["id"] == p["suggestions"][0]["annotation_id"]
                for a in self.s.snapshot(self.pid)["annotations"]
            )
        )
        self.s.review(self.pid, s["id"], "rejected")
        self.assertEqual(
            self.s.snapshot(self.pid)["suggestions"][0]["status"], "rejected"
        )
        self.s.review(self.pid, s["id"], "undo")
        self.assertEqual(
            self.s.snapshot(self.pid)["suggestions"][0]["status"], "pending"
        )

    def test_pose_sync_missing_and_schema(self):
        pose = self.p["pose"]
        validate_pose(pose, 8000)
        self.assertEqual(nearest_frame(pose, 2050)["timeMs"], 2000)
        self.assertIsNone(nearest_frame(pose, 10000))
        self.assertEqual(nearest_frame(pose, 1000)["timeMs"], 1000)
        broken = json.loads(json.dumps(pose))
        broken["frames"][0]["points"]["head"] = [2, 0.3]
        with self.assertRaises(ValidationError):
            validate_pose(broken, 8000)

    def test_eaf_unicode_equal_distinct_slots_offset_roundtrip(self):
        pid = import_eaf(self.s, EAF)
        xml = export_eaf(self.s, pid)
        root, annotations = parse_eaf(xml)
        self.assertEqual(len(annotations), 2)
        self.assertEqual(annotations[0]["value"], "你好 & demo")
        self.assertEqual(
            root.find("./HEADER/MEDIA_DESCRIPTOR").get("TIME_ORIGIN"), "125"
        )
        self.assertEqual(root.find("./HEADER/PROPERTY").text, "臺灣 & gestures")
        self.assertEqual(
            {n.get("TIME_SLOT_ID") for n in root.findall("./TIME_ORDER/TIME_SLOT")},
            {"ts1", "ts2", "ts3", "ts4"},
        )
        pid2 = import_eaf(self.s, xml)
        self.assertEqual(
            sorted(
                (a["start"], a["end"], a["value"])
                for a in self.s.snapshot(pid2)["annotations"]
            ),
            sorted(
                (a["start"], a["end"], a["value"])
                for a in self.s.snapshot(pid)["annotations"]
            ),
        )

    def test_eaf_fail_closed_no_changes(self):
        for xml in [
            EAF.replace('TIME_VALUE="100"', ""),
            EAF.replace('TIME_SLOT_ID="ts3"', 'TIME_SLOT_ID="ts1"'),
            EAF.replace('TIER_ID="眉毛"', 'TIER_ID="眉毛" PARENT_REF="慣用手"'),
            EAF.replace('TIME_SLOT_REF1="ts3"', 'TIME_SLOT_REF1="ts1"'),
            EAF.replace(
                "<ANNOTATION_VALUE>示例</ANNOTATION_VALUE>",
                '<REF_ANNOTATION ANNOTATION_REF="a2"/>',
            ),
            EAF.replace(
                "</ANNOTATION_DOCUMENT>",
                '<CONTROLLED_VOCABULARY CV_ID="cv"/></ANNOTATION_DOCUMENT>',
            ),
            '<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + EAF,
        ]:
            before = len(self.s.rows("SELECT id FROM projects"))
            with self.assertRaises(ValidationError):
                import_eaf(self.s, xml)
            self.assertEqual(len(self.s.rows("SELECT id FROM projects")), before)

    def test_demo_eaf_roundtrip(self):
        xml = export_eaf(self.s, self.pid)
        root, anns = parse_eaf(xml)
        self.assertEqual(len(anns), 2)
        pid = import_eaf(self.s, xml)
        self.assertEqual(len(self.s.snapshot(pid)["annotations"]), 2)


if __name__ == "__main__":
    unittest.main()
