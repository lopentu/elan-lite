"""Offline adapter for already extracted MediaPipe-like landmark JSON. No inference/upload."""

import argparse, json
from .core import validate_pose, ValidationError


def adapt_results(source):
    """Input: model/version/topologyVersion, durationMs, frames of timeMs + named groups.
    Groups contain x/y landmarks or null for a missing detection. z is explicitly ignored.
    """
    model = source["model"]
    groups = source["groups"]
    frames = []
    names = []
    edges = []
    for group, spec in groups.items():
        count = spec["count"]
        names.extend(f"{group}:{i}" for i in range(count))
        edges.extend([f"{group}:{a}", f"{group}:{b}"] for a, b in spec.get("edges", []))
    for frame in source["frames"]:
        points = {}
        for group, spec in groups.items():
            landmarks = frame.get(group)
            if landmarks is None:
                continue
            if len(landmarks) != spec["count"]:
                raise ValidationError("Detection size does not match declared topology")
            for i, p in enumerate(landmarks):
                if p is not None:
                    points[f"{group}:{i}"] = [p["x"], p["y"]]
        frames.append({"timeMs": frame["timeMs"], "points": points})
    pose = {
        "coordinateSystem": "normalized-image-2d",
        "model": model,
        "topology": {
            "version": source["topologyVersion"],
            "names": names,
            "edges": edges,
            "motionPoints": source.get("motionPoints", []),
        },
        "transforms": source.get("transforms", {"mirrored": False, "offsetMs": 0}),
        "frames": frames,
        "adapter": "mediapipe-json-2d-v1",
        "discardedFields": ["z", "worldLandmarks", "segmentation", "blendshapes"],
        "sourceCoordinateSystem": "normalized-image-estimates",
    }
    validate_pose(pose, source["durationMs"])
    return pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    with open(args.input) as f:
        source = json.load(f)
    pose = adapt_results(source)
    with open(args.output, "w") as f:
        json.dump(pose, f, ensure_ascii=False, indent=2)
    print(
        "Wrote 2D estimates; no calibrated 3D; discarded:",
        ", ".join(pose["discardedFields"]),
    )


if __name__ == "__main__":
    main()
