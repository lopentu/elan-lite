# Pose, model adapters and research caveats

Official documentation researched on 2026-10-14:

- [MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker): estimates 33 body landmarks, normalized image and inferred world coordinates. Model outputs are estimates.
- [Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker): hand landmarks and handedness, not signing dominance or TSL gloss recognition.
- [Holistic Tasks](https://developers.google.com/edge/mediapipe/solutions/vision/holistic_landmarker): currently 553 landmarks (478 face + 33 pose + 21 per hand). Legacy Holistic uses a different topology (543). Do not assume a fixed dimension.
- [Holistic JavaScript API](https://developers.google.com/edge/api/mediapipe/js/tasks-vision.holisticlandmarker): video inference timestamps are milliseconds; synchronous inference should be isolated from rendering. Backward seeks require explicit tracker reset / sequential extraction in a future live adapter.

No trained model executes in this MVP. No downloads of model weights, API key prompts, account agreements or paid resources are needed. The implemented offline adapter transforms **already extracted local** results; browser inference / model fetching is future functionality.

## Structured pose JSON

```json
{
  "coordinateSystem": "normalized-image-2d",
  "model": {"name": "synthetic-stick-figure", "version": "1", "trained": false},
  "topology": {
    "version": "custom-v1", "names": ["leftWrist", "rightWrist"],
    "edges": [["leftWrist", "rightWrist"]],
    "motionPoints": ["leftWrist", "rightWrist"]
  },
  "transforms": {"mirrored": false, "offsetMs": 0},
  "frames": [
    {"timeMs": 0, "points": {"leftWrist": [0.3, 0.6], "rightWrist": [0.7, 0.5]}},
    {"timeMs": 100, "points": {}}
  ]
}
```

Coordinates are `[x,y]` normalized to the full video image (top-left origin). Only finite values in `[0,1]` are accepted. Names and edges are topology-specific; timestamp order is strictly increasing integer milliseconds. Empty points records represent missing detections. No interpolation across absent detections: overlay uses the nearest frame only within 150 ms. Backward seek recalculates from timestamp; no tracker state is reused. `annotation_time = pose_frame_time + offsetMs`; rendering can mirror x explicitly. Loci are separately researcher-entered coordinates attached to annotation provenance, displayed during its interval. The skeleton is intentionally sparse and cannot capture handshape or nonmanual semantics completely.

For already extracted MediaPipe-shaped JSON:

```bash
python -m backend.pose_adapter local-results.json local-pose.json
```

Input declares `model` (include exact model/task version), `topologyVersion`, `durationMs`, `groups` with `count` / `edges`, optional `motionPoints`, `transforms`, and `frames` with `timeMs` and group arrays of `{x,y,z?}`. A null group means missing detection. Output names are `group:index`, so declare wrist points such as `pose:15`, `pose:16` in `motionPoints`. This allows different Holistic topologies without assumptions. The adapter explicitly lists discarded z / world landmarks / segmentation / blendshape fields and prints that loss; keep your original results. It does **not** convert estimated world coordinates into calibrated 3D. Only 2D display is supported.

## Working proposer

`motion-boundary-v1` computes maximum displacement per second for declared `motionPoints` (or names containing wrist), threshold **0.12 normalized image units/s**, minimum run **300 ms**, and stops on missing detections / sample gaps over 250 ms. Thresholds are engineering defaults, not corpus-validated linguistic boundaries. The synthetic fixture produces inspectable candidates. A hold or pause is not necessarily a sign boundary; movements can belong to transitions, coarticulation, non-sign gestures or camera motion. The proposer does not output TSL vocabulary.

Candidates retain provider / version, heuristic kind, threshold, input model/topology and creation time. Accept produces a separate annotation containing proposal ID and original interval. Edited annotations retain provenance. Reject records status and review time; undo restores pending and removes the created annotation. Proposal history is inspectable but is not an immutable audit ledger or human identity system. Re-running proposals skips previously proposed identical intervals.

Future model providers should return candidates into this review path, never overwrite gold annotations automatically. Record source hash, exact model weight version, preprocessing, timestamps, confidence semantics, training domain, consent scope and evaluation split. External inference must require an explicit deployment design and participant consent; none is enabled here.

## Research validity

No corpus was supplied; all tests concern software behavior, not recognition or linguistic validity. A TSL study needs Deaf / native signer participation, an agreed annotation convention, dialect/variant handling, appropriate consent/retention, dual annotation and disagreement review. Evaluate signer-disjoint datasets and uncertainty; do not report heuristic thresholds as model accuracy. Dominance, laterality and camera mirroring must be explicitly checked. Occlusion, rapid motion and hand/face detail make sparse pose insufficient. Model-derived 3D is not a substitute for calibrated capture.
