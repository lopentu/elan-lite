# EAF interoperability contract

Reference: official [EAF 3.0 format](https://www.mpi.nl/tools/elan/EAF_Annotation_Format_3.0_and_ELAN.pdf), [schema](https://www.mpi.nl/tools/elan/EAFv3.0.xsd) and [ELAN validation workflow](https://www.mpi.nl/tools/elan/docs/manual/Sec_Validating_EAFfile.html), inspected 2026-10-14.

EAF is a graph of time slots, annotation references, tiers, linguistic types and vocabulary / external references. This MVP supports a deliberately narrow editable subset. It does not flatten reference annotations into editable intervals.

## Accepted

EAF 2.8 / 3.0 documents with one millisecond HEADER, one TIME_ORDER, independent TIERs referring to time-alignable LINGUISTIC_TYPEs, and ALIGNABLE_ANNOTATIONs with one ANNOTATION_VALUE. Annotation values may contain Unicode, including Traditional Chinese and escaped XML characters. Same-tier intervals cannot overlap.

Allowed root attributes: AUTHOR, DATE, VERSION, FORMAT, xsi:noNamespaceSchemaLocation. Header metadata: MEDIA_FILE, TIME_UNITS; MEDIA_DESCRIPTOR with MEDIA_URL, RELATIVE_MEDIA_URL, MIME_TYPE, TIME_ORIGIN, EXTRACTED_FROM; PROPERTY NAME and text. Tier metadata: TIER_ID, LINGUISTIC_TYPE_REF, PARTICIPANT, ANNOTATOR. Type metadata: LINGUISTIC_TYPE_ID, TIME_ALIGNABLE, GRAPHIC_REFERENCES. Parser checks element placement, IDs, references, integer times and duplicate IDs. IDs must be ASCII XML IDs in this subset; Unicode IDs are explicitly rejected, while Unicode tier names / values are accepted.

Original accepted EAF XML is retained verbatim in SQLite and included in the JSON backup. Export reconstructs the editable annotations while preserving accepted header/tier/type metadata and original slot IDs. Equal-valued slots on different independent tiers **remain distinct**. Unused original slots are retained. XML whitespace/prefix spelling and comments are not round-tripped; semantic metadata is. Application-generated files use distinct slots and one independent time-alignable linguistic type. Generated files have been tested against the official 3.0 XSD; import itself uses domain validation, not a full XML Schema engine.

## Rejected, with a visible report and no database writes

- REF_ANNOTATION, ANNOTATION_REF, PREVIOUS_ANNOTATION; Symbolic_Association / Symbolic_Subdivision.
- Parent tiers, Time_Subdivision, Included_In and constraint stereotypes.
- Shared TIME_SLOT identities across annotation boundaries (including intentionally dependent shared slots). The editor cannot safely propagate such edits yet.
- Absent TIME_VALUE. Missing values are never converted to zero. Malformed IDs / references, duplicate IDs, cyclic reference content and overlapping same-tier intervals are blocked.
- Controlled vocabularies, CV_ENTRY_ML / CVE_VALUE / CVE_REF, language / locale metadata, lexicon service references, external references, reference link sets, licenses, SVG references and linked files.
- Unknown elements / attributes, non-millisecond time units, DTDs / entities, oversized XML, unsupported document versions.

CV entry IDs are vocabulary-scoped in full EAF. Future support must preserve those scopes rather than treating CVE_ID as globally unique. Researcher lexicon IDs in this MVP are a separate application namespace.

Rejected files remain unchanged on disk; the application does not create a partially imported project or a lossy export. Open them in full ELAN. Read-only preservation of arbitrary unsupported graphs is future work, not an implemented capability.

## Media and extensions

Import never follows MEDIA_URL or a relative path. Users explicitly choose a local browser File. TIME_ORIGIN / paths are retained separately from annotation time. The UI initializes a session-only media origin from the first descriptor; verify it matches the selected file. Multiple media descriptors are preserved as metadata but simultaneous synchronized media is unsupported. Browser blob URLs are never stored / exported. New application projects omit media descriptors instead of inventing machine paths.

EAF export includes time-aligned text and supported EAF metadata, **not** application lexicon links, pose, spatial loci or AI provenance. The UI states this beside the export controls and in export status. Save a JSON backup or copy the SQLite database for complete research state. Do not mistake EAF alone for a full project backup.

Actual desktop ELAN reopen remains unverified. Validate exported documents in desktop ELAN (File → Validate EAF File), inspect the report and media alignment, then save a separate corpus copy. Schema validity alone does not prove linguistic correctness or full ELAN compatibility.
