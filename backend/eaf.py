"""Fail-closed independent aligned EAF subset; preserve accepted XML and slot identity."""

import json, re
from xml.etree import ElementTree as ET
from .core import ValidationError, uid, validate_interval

ALLOWED = {
    "ANNOTATION_DOCUMENT": {
        "AUTHOR",
        "DATE",
        "FORMAT",
        "VERSION",
        "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation",
    },
    "HEADER": {"MEDIA_FILE", "TIME_UNITS"},
    "MEDIA_DESCRIPTOR": {
        "MEDIA_URL",
        "RELATIVE_MEDIA_URL",
        "MIME_TYPE",
        "TIME_ORIGIN",
        "EXTRACTED_FROM",
    },
    "PROPERTY": {"NAME"},
    "TIME_ORDER": set(),
    "TIME_SLOT": {"TIME_SLOT_ID", "TIME_VALUE"},
    "TIER": {"TIER_ID", "LINGUISTIC_TYPE_REF", "PARTICIPANT", "ANNOTATOR"},
    "ANNOTATION": set(),
    "ALIGNABLE_ANNOTATION": {"ANNOTATION_ID", "TIME_SLOT_REF1", "TIME_SLOT_REF2"},
    "ANNOTATION_VALUE": set(),
    "LINGUISTIC_TYPE": {"LINGUISTIC_TYPE_ID", "TIME_ALIGNABLE", "GRAPHIC_REFERENCES"},
}


def parse_eaf(text):
    if (
        len(text) > 5_000_000
        or "<!DOCTYPE" in text.upper()
        or "<!ENTITY" in text.upper()
    ):
        raise ValidationError("Unsafe or oversized XML")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValidationError("Malformed EAF XML: " + str(e))
    errors = []
    allowed_children = {
        "ANNOTATION_DOCUMENT": {"HEADER", "TIME_ORDER", "TIER", "LINGUISTIC_TYPE"},
        "HEADER": {"MEDIA_DESCRIPTOR", "PROPERTY"},
        "TIME_ORDER": {"TIME_SLOT"},
        "TIER": {"ANNOTATION"},
        "ANNOTATION": {"ALIGNABLE_ANNOTATION"},
        "ALIGNABLE_ANNOTATION": {"ANNOTATION_VALUE"},
    }
    for parent in root.iter():
        if any(c.tag not in allowed_children.get(parent.tag, set()) for c in parent):
            errors.append("Invalid or unsupported EAF element placement: " + parent.tag)
    if not root.get("AUTHOR") or not root.get("DATE"):
        errors.append("AUTHOR and DATE are required")
    try:
        import datetime

        datetime.datetime.fromisoformat(root.get("DATE", ""))
    except ValueError:
        errors.append("Invalid EAF DATE")
    global_ids = set()
    for n in root.iter():
        for key in ("TIME_SLOT_ID", "ANNOTATION_ID"):
            if key in n.attrib:
                value = n.get(key)
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value or ""):
                    errors.append(
                        "Only ASCII XML IDs are supported (Unicode annotation text is supported)"
                    )
                if value in global_ids:
                    errors.append("Duplicate XML ID across elements")
                global_ids.add(value)
    if root.tag != "ANNOTATION_DOCUMENT" or root.get("VERSION") not in ("2.8", "3.0"):
        errors.append("Only EAF 2.8/3.0 annotation documents supported")
    required = {
        "MEDIA_DESCRIPTOR": {"MEDIA_URL", "MIME_TYPE"},
        "TIME_SLOT": {"TIME_SLOT_ID"},
        "TIER": {"TIER_ID", "LINGUISTIC_TYPE_REF"},
        "ALIGNABLE_ANNOTATION": {"ANNOTATION_ID", "TIME_SLOT_REF1", "TIME_SLOT_REF2"},
        "LINGUISTIC_TYPE": {"LINGUISTIC_TYPE_ID"},
    }
    for node in root.iter():
        if any(not node.get(key) for key in required.get(node.tag, set())):
            errors.append("Missing required attributes: " + node.tag)
        if node.tag == "MEDIA_DESCRIPTOR" and "TIME_ORIGIN" in node.attrib:
            try:
                int(node.get("TIME_ORIGIN"))
            except ValueError:
                errors.append("Invalid media TIME_ORIGIN")
        if node.tag == "LINGUISTIC_TYPE" and node.get(
            "GRAPHIC_REFERENCES", "false"
        ) not in ("true", "false", "1", "0"):
            errors.append("Invalid GRAPHIC_REFERENCES")
    if "T" not in root.get("DATE", ""):
        errors.append("EAF DATE must be a dateTime")
    rank = {"HEADER": 0, "TIME_ORDER": 1, "TIER": 2, "LINGUISTIC_TYPE": 3}
    ranks = [rank.get(n.tag, 99) for n in root]
    if ranks != sorted(ranks):
        errors.append("Invalid EAF element order")
    for node in root.iter():
        if node.tag not in ALLOWED:
            errors.append("Unsupported element: " + node.tag)
            continue
        unknown = set(node.attrib) - ALLOWED[node.tag]
        if unknown:
            errors.append(
                "Unsupported attributes on "
                + node.tag
                + ": "
                + ", ".join(sorted(unknown))
            )
    header = root.find("HEADER")
    if header is None or header.get("TIME_UNITS", "milliseconds") != "milliseconds":
        errors.append("Exactly one millisecond HEADER is required")
    if len(root.findall("HEADER")) != 1 or len(root.findall("TIME_ORDER")) != 1:
        errors.append("Exactly one HEADER and TIME_ORDER required")
    slots = {}
    types = {}
    tier_names = set()
    annotation_ids = set()
    annotations = []
    for n in root.findall("./TIME_ORDER/TIME_SLOT"):
        sid = n.get("TIME_SLOT_ID")
        val = n.get("TIME_VALUE")
        if not sid or sid in slots:
            errors.append("Duplicate/missing time slot ID")
        if val is None:
            errors.append("Missing TIME_VALUE is unsupported; never converted to zero")
        try:
            v = int(val)
            assert v >= 0
        except (TypeError, ValueError, AssertionError):
            v = None
            errors.append("Invalid time slot value")
        slots[sid] = v
    for n in root.findall("LINGUISTIC_TYPE"):
        tid = n.get("LINGUISTIC_TYPE_ID")
        if not tid or tid in types:
            errors.append("Duplicate/missing linguistic type ID")
        if n.get("TIME_ALIGNABLE", "true") != "true":
            errors.append("Reference linguistic types unsupported")
        types[tid] = n
    for tier in root.findall("TIER"):
        tid = tier.get("TIER_ID")
        if not tid or tid in tier_names:
            errors.append("Duplicate/missing tier ID")
        tier_names.add(tid)
        if tier.get("LINGUISTIC_TYPE_REF") not in types:
            errors.append("Unknown linguistic type")
        intervals = []
        for wrapper in tier:
            if (
                wrapper.tag != "ANNOTATION"
                or len(wrapper) != 1
                or wrapper[0].tag != "ALIGNABLE_ANNOTATION"
            ):
                errors.append("Only aligned annotations supported")
                continue
            a = wrapper[0]
            aid = a.get("ANNOTATION_ID")
            s1 = a.get("TIME_SLOT_REF1")
            s2 = a.get("TIME_SLOT_REF2")
            if not aid or aid in annotation_ids:
                errors.append("Duplicate/missing annotation ID")
            annotation_ids.add(aid)
            start = slots.get(s1)
            end = slots.get(s2)
            if start is None or end is None or start >= end:
                errors.append("Invalid or missing interval references")
                continue
            if len(a) != 1 or a[0].tag != "ANNOTATION_VALUE":
                errors.append("Exactly one annotation value required")
            if any(start < e and end > s for s, e in intervals):
                errors.append("Same-tier overlap unsupported")
            intervals.append((start, end))
            annotations.append(
                {
                    "id": aid,
                    "tier": tid,
                    "start": start,
                    "end": end,
                    "start_slot": s1,
                    "end_slot": s2,
                    "value": a.findtext("ANNOTATION_VALUE", ""),
                }
            )
    # Shared slots cannot be independently moved safely in this MVP.
    uses = {}
    for a in annotations:
        for field in ("start_slot", "end_slot"):
            uses[a[field]] = uses.get(a[field], 0) + 1
    if any(count > 1 for count in uses.values()):
        errors.append(
            "Shared TIME_SLOT dependencies unsupported for editing; original EAF remains unchanged"
        )
    if errors:
        raise ValidationError(
            "Import blocked; no changes made. " + "; ".join(dict.fromkeys(errors))
        )
    return root, annotations


def import_eaf(store, text):
    root, annotations = parse_eaf(text)
    pid = uid()
    duration = max([a["end"] for a in annotations] + [8000])
    pose = {
        "coordinateSystem": "normalized-image-2d",
        "model": {"name": "none", "version": "1"},
        "topology": {"version": "empty-v1", "names": ["placeholder"], "edges": []},
        "transforms": {"offsetMs": 0, "mirrored": False},
        "frames": [],
    }
    with store.db:
        store.db.execute(
            "INSERT INTO projects VALUES(?,?,?,?,?)",
            (pid, "EAF 匯入 / Imported EAF", duration, json.dumps(pose), text),
        )
        tiers = {}
        for tier in root.findall("TIER"):
            tid = uid()
            tiers[tier.get("TIER_ID")] = tid
            store.db.execute(
                "INSERT INTO tiers VALUES(?,?,?,?,?)",
                (tid, pid, tier.get("TIER_ID"), "imported", "#7aabff"),
            )
        for a in annotations:
            store.db.execute(
                "INSERT INTO annotations VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    uid(),
                    tiers[a["tier"]],
                    a["start"],
                    a["end"],
                    a["value"],
                    None,
                    json.dumps({"source": "eaf", "originalAnnotationId": a["id"]}),
                    a["start_slot"],
                    a["end_slot"],
                ),
            )
    return pid


def export_eaf(store, pid):
    p = store.snapshot(pid)
    source = store.rows("SELECT source_eaf FROM projects WHERE id=?", (pid,))[0][
        "source_eaf"
    ]
    if source:
        root = ET.fromstring(source)
        for t in root.findall("TIER"):
            for a in list(t):
                t.remove(a)
        order = root.find("TIME_ORDER")
        original_slots = {n.get("TIME_SLOT_ID"): n.get("TIME_VALUE") for n in order}
        order.clear()
        by_name = {n.get("TIER_ID"): n for n in root.findall("TIER")}
        tier_map = {t["id"]: by_name[t["name"]] for t in p["tiers"]}
    else:
        root = ET.Element(
            "ANNOTATION_DOCUMENT",
            AUTHOR="ELAN-lite",
            DATE="2026-10-14T00:00:00Z",
            FORMAT="3.0",
            VERSION="3.0",
        )
        ET.SubElement(root, "HEADER", TIME_UNITS="milliseconds")
        order = ET.SubElement(root, "TIME_ORDER")
        tier_map = {}
        for t in p["tiers"]:
            tier_map[t["id"]] = ET.SubElement(
                root, "TIER", TIER_ID=t["name"], LINGUISTIC_TYPE_REF="independent"
            )
        ET.SubElement(
            root,
            "LINGUISTIC_TYPE",
            LINGUISTIC_TYPE_ID="independent",
            TIME_ALIGNABLE="true",
            GRAPHIC_REFERENCES="false",
        )
    # Distinct slots stay distinct even with equal timestamps.
    slots = []
    if source:
        used = {a[k] for a in p["annotations"] for k in ("start_slot", "end_slot")}
        slots.extend(
            (sid, int(value))
            for sid, value in original_slots.items()
            if sid not in used
        )
    for a in p["annotations"]:
        s1 = a["start_slot"] or uid()
        s2 = a["end_slot"] or uid()
        slots.extend([(s1, a["start"]), (s2, a["end"])])
        wrap = ET.SubElement(tier_map[a["tier_id"]], "ANNOTATION")
        node = ET.SubElement(
            wrap,
            "ALIGNABLE_ANNOTATION",
            ANNOTATION_ID=a["provenance"].get("originalAnnotationId", a["id"]),
            TIME_SLOT_REF1=s1,
            TIME_SLOT_REF2=s2,
        )
        ET.SubElement(node, "ANNOTATION_VALUE").text = a["value"]
    for sid, t in sorted(slots, key=lambda s: s[1]):
        ET.SubElement(order, "TIME_SLOT", TIME_SLOT_ID=sid, TIME_VALUE=str(t))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
