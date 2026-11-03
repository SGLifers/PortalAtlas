# Handoff

## User request

Build a local web app using the game assets already on this system. Portal walls
are destination nodes; angles/movement are directed edges. Create a separate Git
repository, commit milestones, document handoffs, and persist until complete.
No video/screenshot reconstruction. No deployment requested.

## State — 2026-11-02 America/Los_Angeles

- New repository: /home/lambchopper67/Documents/ChatGPT/Splitgate/PortalAtlas
- Branch: codex/portal-atlas
- Source located in immutable Docker image splitgate-host:private-game-payload
  (2a8c85545524), under /game/PortalWars2/Content/Paks.
- Archives: pakchunk0/100/200/300/400/500, plus 400optional and global.
  Both .pak and UE IoStore .utoc/.ucas exist, about 40 GB total.
- Separate live SplitgateHost worker exists: do not touch it or its repository.
- No game has been launched, no game files modified, no map geometry extracted.
- Host lacks node/npm/dotnet on PATH. Bundled Node:
  /home/lambchopper67/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
- Python3 and Docker are available. Free disk approximately 466 GB.
- Read the Sites skill and local preview reference. Local-only workflow applies.

## Next actions

1. Inspect archive headers and obtain a compatible CUE4Parse CLI/runtime.
2. Mount archives in an isolated read-only container or copy only needed assets
   into ignored data/. Determine whether encryption/mappings are required.
3. Extract one real map with portal walls and geometry, then implement the web
   viewer and graph pipeline. Preserve exact source/version/provenance.
4. Validate and commit each meaningful milestone; update this file.

## Research pointers

- https://github.com/FabianFG/CUE4Parse
- https://github.com/4sval/FModel
- https://www.gildor.org/smf/index.php?topic=9225.0
  Maintainer reports UE5.5 and a game-specific override; do not assume vanilla
  parsing or encryption compatibility without testing the local build.
- https://github.com/sinnafuls/cue4parse-mcp (release binary is Windows only).

## Acceptance remaining

All implementation, extraction, route validation, browser QA, and delivery.

## Milestone 2 — archive decryption, 2026-11-02

- Installed ignored local .NET SDK 10.0.403 and built CUE4Parse commit
  d3f153e1aac51808b3d5e7d23c1451fcc70bae85, native build skipped.
- All archives copied to data/install/Paks (about 37 GB). Shipping executable is
  data/install/Shipping.exe (duplicate original-name copy also exists).
- Isolated container portal-atlas-assets is stopped; safe to remove after source
  preparation. Never touch splitgate-selection284-host-1 or other host workers.
- Static key recovered from callback raw 0x890d360: the LEA at 0x890d375 points to
  four obfuscated qwords; ROL64 by 8 decodes them, then delegate wrapper at
  0x4b1ec82 XORs byte 10 with 0x2f. tools/extract_key.py reproduces this with build
  SHA256 and opcode guards. Key remains ignored in data/key.txt.
- VALIDATED: original archives mount 215,239 files with GAME_Splitgate2.
- 1,794 .umap packages indexed in data/maps-index.json; 34 map feature namespaces
  identified. Portal meshes and Academy_Portals sublevel exist.
- First real map dump correctly refuses: unversioned properties require mappings.
  No .usmap exists inside the game archive. Geometry is not yet extracted.
- Research now targets offline native reflection schemas. No game launch,
  injection, screenshot, video, or runtime game-memory reading occurred.
- Tooling experiments live under ignored .tools/. They are investigation artifacts,
  not the reproducible pipeline yet. Several failed key scans are retained there.

### Reproduce archive listing

```bash
python3 tools/extract_key.py data/install/Shipping.exe data/key.txt
ATLAS_KEY_FILE=data/key.txt .tools/dotnet/dotnet \
  tools/AssetReader/bin/Release/net10.0/AssetReader.dll \
  data/install/Paks list .umap data/maps-index.json
```

### Current investigation

- Many native struct/enum registration records recovered statically into
  data/native-registrations.json. Class tables/property params appear partly in
  zero-initialized .data, requiring metadata initializer analysis.
- .tools/inspect_pe.py disassembles one function using .pdata; leaf functions may
  be omitted from .pdata, so check exact instructions independently.
- .tools/relrefs.py uses NumPy to find RIP references; run using bundled Python
  (system Python lacks NumPy). Add --rva for a virtual address in .data/BSS.
- Installing Unicorn into .tools/python for isolated metadata emulation, if
  necessary. This must never start the executable or run a game session.
- .tools/check_native.py verified CUE4Parse's custom AES output against only the
  standalone stateless AES routine. Do not use it in the delivered application.
