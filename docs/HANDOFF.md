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

## Milestone 3 — real map viewer and graph, 2026-11-02

### Running app

- Local server: `python3 -m server --port 8741` (retained exec session 42500).
- URL: http://127.0.0.1:8741
- CUA browser tab 2 in iab browser 2 is open for QA, variable `tab` exists.
- UI loads installed asset geometry, wall nodes, directed graph; selects routes
  by time/difficulty; supports unavailable walls, movement filters, local saved
  routes, JSON export, map import jobs, source notes, 3D/top views.
- Just added default cutaway clipping and aspect-aware camera fit after first
  browser screenshot showed the arena's exterior shell obstructing the view.
  Reload browser before checking those changes.

### Real extracted datasets

- Academy: 69 walls, 360 edges, 33 active levels.
- Abyss: 58 walls, 206 edges.
- Grit: 75 walls, 221 edges.
- Oasis: 76 walls, 685 edges.
- Data ignored under data/extracted/ (per-package JSON, mesh binary+metadata,
  feature manifests), data/scenes/ (compiled web scene+graph).
- All coordinates and map geometry are from game assets. No synthetic maps,
  videos, screenshots, or game process used for map reconstruction.
- Compilers follow always-loaded levels, then use generated World Partition
  cells where present. Dynamic pregame/menu levels are excluded.
- `tools/compile_scene.py` runs with bundled Python (NumPy), about 20–35 sec/map.
  Render geometry is an explicitly labeled collision proxy. Movement/jump/time
  parameters are estimates. Launch momentum and paths around corners are not
  yet modeled; do not describe them as verified.
- `server/routing.py` uses Dijkstra over wall + face state; wall remains the
  user-facing node. Avoids silently switching faces mid-route.
- `FeatureExporter` retains direct mesh objects resolved through package IDs;
  re-opening remastered meshes by displayed path can fail. This fixed hundreds
  of false missing-mesh errors for Abyss/Oasis. Oasis now exports 532 meshes with
  zero caught extraction exceptions. Full Serilog deserialization errors still
  need to be included in manifests.

### Offline reflection breakthrough

- Native property definitions use FNames initialized by small helper routines.
- `.tools/emulate_metadata.py` emulates isolated `.CRT$XCU` helpers in Unicorn,
  not the game entrypoint, intercepting FName storage and security-cookie check.
  91,894 helpers: 72,637 complete, 19,257 fail; captures 37,687 unique names.
- Intermediate data/reflection-data.bin is a private initialized .data overlay;
  data/reflection-names.json holds the synthetic lookup used for schema recovery.
- `.tools/parse_metadata.py`, `.tools/build_mappings.py` derive native schemas
  into data/mappings.json. Currently 9,770 types; 4,638 schemas rejected rather
  than inventing missing data. Essential SceneComponent/PrimitiveComponent/
  StaticMeshComponent/Actor/GF1047PortalWall schemas decode real geometry.
- Blueprint schemas are read by CUE4Parse from assets. One recurring nongeometry
  PortalWarsWorldSettings error remains (native schema initialization failure).
- IMPORTANT: reflection scripts currently remain prototype files in ignored
  .tools/. Make them tracked, clean, reproducible tools before delivery.
- Class param counts: `(counts >> 15) & 2047`, not just >>15 (interfaces share
  the word). Type reference resolution follows native construction routines.
- Native property ArrayDim/Offset are uint16 at +48/+50, GenFlags at +24.
- CUE4Parse prints property index suffixes like RelativeLocation[27] even for
  scalars; compiler strips those numeric suffixes.

### Remaining before completion

1. Browser QA after cutaway/camera fix; exercise route search, save/export,
   map switching/import, filters, and narrow viewport; fix observed failures.
2. Promote/refactor offline reflection and setup tooling into tracked source.
3. Record all extraction warnings/errors; improve needed schemas if possible.
4. Meaningful geometry/routing/integration tests and asset-derived invariants.
5. Expand installed map coverage with the importer; report unsupported map
   layouts honestly (World Partition/FastGeo may need additional extraction).
6. README, setup/run scripts, provenance/limitations, final commits and handoff.
7. Clean up owned stopped portal-atlas-assets container; keep live host alone.

### Runtime paths

Bundled Python (with NumPy):
`/home/lambchopper67/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`
Bundled Node:
`/home/lambchopper67/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node`
Local .NET: `.tools/dotnet/dotnet`
Local Python extras: `.tools/python` (capstone, pefile, unicorn).

### Important verification limits

- No automated in-game movement execution or measured difficulty calibration.
- Graph currently uses center-target direct placement rays, floor-supported
  straight movement and conservative approximate jump arcs. It is not an
  exhaustive enumeration of all possible portal placements or momentum routes.
- Failure notes and source package paths are visible in the UI and exports.
