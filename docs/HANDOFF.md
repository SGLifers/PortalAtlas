# Handoff — completed, 2026-11-03

## User request and delivery

The user authorized a local web app reading installed game assets, with portal
walls as destination nodes and angles/movement as directed edges carrying costs
and difficulty. They required a new local repo, incremental commits and handoff
docs, and asked us to persist until done. This deliverable is complete.

- App: http://127.0.0.1:8741
- Repo: /home/lambchopper67/Documents/ChatGPT/Splitgate/PortalAtlas
- Branch: codex/portal-atlas, independent repository, no remote.
- 25 standalone arena/training datasets:3,432walls,14,722edges,2,234terrainpatches.
- All25 pass geometry coverage and graph/buffer audit. 40 tests pass.
- Browser QA and per-map counts: [VALIDATION.md](VALIDATION.md).
- Screenshot: .local/portal-atlas-preview.jpg (app QA only, never map input).
- Keep the server running for the user. Current owned daemon PID1044582;
  .local/server.pid and .local/server.log identify it. Verify /proc/PID/cwd and
  command before signaling a process. No background import jobs remain.

## Run and verify

```bash
cd /home/lambchopper67/Documents/ChatGPT/Splitgate/PortalAtlas
./run.sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_maps.py
.venv/bin/python tools/import_maps.py --all-arenas --refresh
```

Only start run.sh if the existing server is stopped or use another --port.
The browser tab3 is marked deliverable (cua binding atlasTab, browser2). After
context continuation, call cua.rewriteDocumentation() before interacting with it.
No viewport override remains. Two saved Academy QA routes and JSON downloads are
in the browser/Downloads. The current page shows Academy P01→P06.

For dependencies/setup, run ./setup.sh. It passed against the prepared cache.
Node is available at:
/home/lambchopper67/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
Build reader with:
`CUE4PARSE_SKIP_NATIVE=1 DOTNET_PROCESSOR_COUNT=2 .tools/dotnet/dotnet build tools/AssetReader -c Release -m:2`
Keep OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 for analysis and at most4CPUs in use.
Never overwrite the reader DLL while a reader process is using it.

## Asset provenance

Source is immutable local Docker image splitgate-host:private-game-payload,
SHA256 2a8c855455249cf97a452345047e67b7f2a8c66c695784d891b6be13f8d61399.
Copied /game/PortalWars2/Content/Paks into ignored data/install/Paks (35.6GiB).
Shipping.exe SHA256 619e4753e2f68c721764a19afe61b01daee723beaa946ef94ec6bb4e0c7c5747.
The owned stopped snapshot portal-atlas-assets has been removed. Never operate
SplitgateHost or its live worker containers. No game was launched or modified.

CUE4Parse pinned d3f153e1aac51808b3d5e7d23c1451fcc70bae85, .NET10.0.403,
locally ignored in .tools/. The reader directly resolves Microsoft.Bcl.Memory
9.0.14; upstream CUE's own project restore still warns about its9.0.0 reference.
The delivered reader deps use the patched9.0.14 version.

Key recovery is static and build/opcode guarded; secret stays data/key.txt.
GAME_Splitgate2 successfully mounts215,239files, indexing1,794map packages across
34feature namespaces. No .usmap is supplied. Offline bounded Unicorn emulation
of static helpers intercepts FName storage; it never executes a PE entrypoint,
launches a game process, reads live game memory or invokes host OS APIs from game
code. Native metadata tools recover14,358types/2,431enums, rejecting52schemas.
Nongeometry camera warnings remain in source notes; geometry failures gate edges.

## Pipeline and implementation

- tools/prepare_assets.py, extract_key.py, reflection_emulator.py,
  native_metadata.py, build_mappings.py and setup.py reproduce preparation.
- AssetReader exports conventional/instanced/FastGeo meshes and body setups,
  actual portal actors/transforms/properties, heightmaps at collision mip with
  visibility masks, and blocking brushes with channel responses.
- Cross-feature always-loaded references resolve against archive paths.
- compile_scene.py chooses one root, its loaded/generated cells, builds shared
  mesh BVHs plus instance BVH and directed candidate edges. Flattened zero-scale
  geometry is handled without dropping collidable planes.
- finalize_scene.py checks streaming/brush coverage and filters candidates using
  Pawn/PortalLauncher responses. Model5 + finalizeVersion1 is the current format.
- refresh_coverage.py upgrades old cached brush metadata/scenes without repeating
  the expensive base geometric graph. Recompile if an earlier missing-data gate
  already removed all candidate edges; filtering cannot recreate removed edges.
- import_maps.py --refresh reuses current models; --force re-exports geometry.
  --root on compile_scene.py selects another extracted cooked world.
- Python HTTP API confines files/hosts/origins, guards scene revision and shares
  a file lock between browser/CLI import jobs. It binds127.0.0.1 only.
- Three.js is locally vendored. UI includes3D/top/cutaway, adaptive labels,
  wall picking/search, directed edges, route objectives/filters/avoidance, aiming
  values, saved routes, source notes and native route/full-graph JSON downloads.

## Dataset qualifications

Ozone and Ozone Graffiti only contain shared sublevel libraries. They remain
inspectable in the import catalog but are excluded from the arena list/default
batch. Ozone Night resolves their dependencies (74walls/242edges). HangmanR3 has
16zone walls and0candidate edges. Counts are not a current playlist assertion.

Base walk5.4m/s, sprint multiplier1.5 and nav-agent dimensions are asset-derived.
Timing, difficulty, gravity/jump behavior and active-mode overrides remain
estimates. Portal centers/direct floor corridors/sampled jumps are considered;
corner routes and full momentum state are not. Start with an active portal.
Launch arrivals are terminal until their forced outgoing motion is modeled.
Primitive bounds, render fallbacks and terrain hole boundaries remain proxies;
these results are planning candidates, not measured gameplay guarantees.

## Final verification artifacts

- docs/VALIDATION.md: reproducible checks, per-map counts and browser QA.
- data/validation-report.json and data/import-report.json: all25 ready/pass.
- .local/tests-final.log:40passingtests; .local/audit-final.log:no failures.
- .local/setup-verify.log and .local/build.log: successful setup/build.
- .local/Ozone-final.log, .local/Terra13-final.log: corrected dependency/coverage
  retries. Original failed attempts remain in older logs; reconciled reports are
  authoritative. Fracture457/2086 and Erosion447/1808 successfully compiled with
  terrain and instance acceleration. No original flat-world memory job remains.

No required work remains. Preserve source qualification and reproducibility in
future changes. Git history records each implementation milestone.

## Follow-up — configurable cutoff height, 2026-11-03

The user requested configurable cutaway height. Added a live range slider and
precise number input (world Z metres,0.1m increments), automatic reset and guarded
browser-local per-map persistence. Cutaway off disables the controls and removes
the clipping plane; turning it back on retains the chosen height. Only displayed
geometry is clipped; wall/route overlays and graph calculations are unchanged.
Slider bounds follow scene height bounds and expand for manually entered values.

Browser checks passed: Academy25.4m persists across reload; slider steps to25.3;
Auto restores34.9; Abyss initializes20.1 independently; switching back restores
Academy25.4. Controls disabled/enabled correctly, no console warnings/errors.
At390×844 controls fit without horizontal overflow; override reset afterwards.
JavaScript syntax check passed. No asset recompilation or server restart needed.
Preview: .local/cutoff-height-preview.jpg. Same local server remains running.
