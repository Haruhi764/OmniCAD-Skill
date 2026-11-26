# Tool review and release provenance

The review used locally installed skills, server registration, dependency manifests, source notices and previous execution records. Third-party skill text and code are not vendored.

| Component checked | Strength and evidence | Limits and release decision |
|---|---|---|
| cad-designer 1.2.0 | Scope, unit, annotation and output conventions. Installed skill declares MIT | A drawing count does not resolve conflicting requirements. Capture each drawing and view independently |
| cad-automation 1.3.0 | Installed MIT skill distinguishes source, model units and native CAD content | Workflow document is not a backend. Implemented an original local CLI |
| cad-drawings 0.4.0 | Installed MIT skill supports inspection. Prior local acceptance verified COM and native DWG reopening | Requires CAD availability for native DWG operations. No copied parser or adapter |
| daihua-cad MCP | Registered local stdio service. The bundle's MIT notice credits its CAD-MCP and CAD-Skills components. Prior sessions observed stale COM proxies | Drawing selection and raw command passthrough can mutate a live session. No MCP dependency or generic raw command passthrough |
| Python/AutoCAD project scripts | Proven patterns for exact file selection, native save and pre/post checks | Collection iteration and measurement properties sometimes failed after mutation. No client scripts or templates copied |
| AutoCAD ActiveX, Core Console and AutoLISP | AutoCAD 2023 and Core Console detected. V1 native validation uses ActiveX via pywin32 | Vendor software is proprietary. Core Console and AutoLISP are not V1 backends |
| Other review directories | Local packages for image redraw and PDF vectorization were present under review | Presence does not establish installation, license clearance or verification. No code included |

Dependencies are installed separately. ezdxf uses MIT. The checked distributions of pywin32, pypdf and Pillow report PSF, BSD-3-Clause and MIT-CMU respectively. Poppler is a separate local executable. Dependencies, drivers and fonts retain their own terms. No software binaries, fonts, credentials or customer data are distributed here.

## V1.2 design review

- Local Daihua integration inventory identifies [CAD-MCP](https://github.com/daobataotie/CAD-MCP) at ef26482579424bb564b8b2ccc24f29f133f66fbf (MIT, Copyright (c) 2025 曹瑞), and [cad-skills](https://github.com/delancy827/cad-skills) at 6051169eb3cd39a6539d823261b8519f718828ed (MIT, Copyright (c) 2026 Delancy); integrated by Rain-dust. Reviewed native controller transient COM error handling, fresh attach/document identity, save stages and skill's task-level DXF/native routing. Use the verified approach of exact document binding and bounded transient reads; uncertain writes are stopped, not replayed. No controller or third-party skill code copied. Preserve source license and notice if future reuse goes beyond independent design.
- Existing OmniCAD deterministic geometry, layer/dimension definitions, manifest and layout placement remain in use. Avoid a new visual/layout optimizer or blind translation from screenshot pixels. Validate actual geometry and direction against reviewed inputs, not extra rendering passes. Original additions use only existing dependencies.
- The AutoCAD supervisor is an original Python implementation of atomic state, ownership-safe timeouts, locking and artifact-bound checkpoints.
- Official Autodesk manuals are linked in [LT compatibility](lt-compatibility.md). The separate Experimental tester installs ezdxf and pypdf in its own environment. The ZIP contains a synthetic OmniCAD fixture and the MIT license. Proprietary CAD executables, fonts and third-party dependencies are obtained separately.

The original OmniCAD-Skill project is licensed under the MIT terms in [LICENSE](../LICENSE), with copyright attributed to the OmniCAD-Skill contributors. Review the staged tree and history for credentials, personal paths and client materials before each release. Keep local source paths, fingerprints and test artifacts outside the release.
