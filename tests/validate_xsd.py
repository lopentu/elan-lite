"""Optional official schema verification: python tests/validate_xsd.py /path/EAFv3.0.xsd."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lxml import etree
from backend.core import Store
from backend.eaf import import_eaf, export_eaf
from test_core import EAF

schema = etree.XMLSchema(etree.parse(sys.argv[1]))
store = Store(":memory:")
for pid in [store.demo(), import_eaf(store, EAF)]:
    schema.assertValid(etree.fromstring(export_eaf(store, pid).encode()))
print("PASS: synthetic and imported EAF exports validate against official EAF 3.0 XSD")
