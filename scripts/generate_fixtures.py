"""Reproducible safe fixtures: no real signer or TSL labels."""

import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import itertools
import backend.core as core
from backend.core import Store

sequence = itertools.count(1)
core.uid = lambda: f"id_synthetic_{next(sequence):06d}"
from backend.eaf import export_eaf

s = Store(":memory:")
pid = s.demo()
p = s.snapshot(pid)
folder = pathlib.Path("fixtures")
folder.mkdir(exist_ok=True)
(folder / "synthetic-pose.json").write_text(
    json.dumps(p["pose"], ensure_ascii=False, indent=2)
)
(folder / "synthetic.eaf").write_text(export_eaf(s, pid))
