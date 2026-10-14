# Validation evidence

Cloud compute environment, 2026-10-14. Work performed in a separate writable checkout; original repository MIT LICENSE retained. No participant corpus supplied or used.

- `npm test`: Python unit/integration tests cover persistence through a second SQLite connection, stable lexicon renaming, independent project creation, same-tier overlap rejection, cross-tier half-open overlap queries, reviewed/edited acceptance, rejection and undo, pose validation and timestamp selection, adapter missing detections / topology / explicit 2D conversion, EAF Unicode / distinct equal-valued slots / offsets / round-trips / fail-closed unsupported content, HTTP byte ranges and loopback / cross-origin write guards.
- `npm run build`: strict TypeScript check and Vite production build.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:ui`: actual browser editing and reload persistence, linked glossary rename, overlap query, accept/reject/undo, forward/backward seek synchronized pose overlay and clock, unsupported EAF report, desktop and 390 px mobile layout. Screenshots inspected directly; corrected file-input visibility and mobile ruler overflow.
- `python tests/validate_xsd.py /tmp/elan-EAFv3.0.xsd`: synthetic and imported subset exports passed the official EAF 3.0 XML Schema using lxml. Official XSD was obtained via the web retrieval tool because the cloud shell HTTP route returned 403; no schema approximation was substituted.
- Browser CDN download was blocked by network policy; system Chromium was used successfully. CI installs Playwright Chromium on GitHub's runner.

Desktop ELAN reopening, actual TSL recognition / linguistic segmentation quality, participant media handling in a real corpus, multi-camera calibration and collaboration are **not validated**. No recognition accuracy is reported. GitHub CI status and exact pushed commit are reported in the delivery conversation; this document does not pre-claim a future CI result.
