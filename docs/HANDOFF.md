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
- Keep the server running for the user. Current owned daemon PID1290306;
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

## Follow-up — Academy map-color prototype, 2026-11-03 (complete)

User approved a one-map proof of concept for original surface colors. Academy is
the pilot; broader map rollout and full textures are separate future work. Never
derive a palette from screenshots or assign colors by material-name guesses.

Added an independent `export-colors` AssetReader command and
`tools/import_colors.py MAP_Academy`. It reads the existing scene and archive
materials without rewriting scenes, collision buffers, portal nodes or edges.
Output `data/appearance/MAP_Academy.json` is ignored by Git. Original archive paths
resolve GameFeature plugin references, including nested dynamic material exports.
Material slot sections and per-component/FastGeo overrides are preserved.

Current recovered data: all459 meshes,441 referenced materials,179 usable color
parameters,262 unresolved materials,1,297 component override arrays; no mesh/level
errors or material exceptions. Raw resolved colors are linear RGB with source
asset/parameter and method. Layered colors are representative approximations;
textures, masks, switches, vertex paint and in-game lighting are not evaluated.
Unresolved surfaces use neutral teal. Colored parameters cover about69% of visible
instanced mesh triangles (triangle count, not measured surface area).

Build: `CUE4PARSE_SKIP_NATIVE=1 DOTNET_PROCESSOR_COUNT=2 .tools/dotnet/dotnet build
tools/AssetReader -c Release -m:2` succeeded; existing upstream restore and nullable
warnings remain as documented earlier. Build log `.local/colors-build.log`.
Import log `.local/MAP_Academy-colors.log`. CLI shares `.local/import.lock` with
the geometry importer. Do not overwrite reader DLLs while an import is running.

`/api/colors/<map>` validates the map, sidecar format/version and scene revision.
Missing/stale color data is optional and keeps neutral geometry available.
Server restarted only this owned Atlas checkout to load the endpoint: current
PID1290306, `.local/server.pid`, same localhost8741. No SplitgateHost, game or
Portle process was modified.

UI changes completed: Surfaces Neutral/Map colors selector,
browser-local preference, material-slot groups, override-aware instancing, shared
cutaway planes, neutral fallback and explanatory status. 7 focused Python color
tests and 5 Node color-validation tests passed. Browser verified colors load,
neutral preference persists, cutoff20m clips colored surfaces and Academy
P01→P06 still reports4steps/4.5s/78difficulty across surface modes.

Final verification: 48 Python tests passed (1.785s), including the original graph,
geometry, API and private-asset checks, plus color endpoint/sidecar checks. Log:
`.local/tests-colors.log`. Five Node tests passed using `node --test
tests/colors.test.mjs`; `node --check web/app.js` passed. The reader's final import
completed with the counts above. Color data and proprietary materials stay ignored.

Browser QA also passed: switching to Abyss disables the color selector with a clear
not-imported message; returning to Academy restores the color preference. At390×844
the surface controls fit without horizontal overflow. Top view works, cutaway off
reveals upper colored geometry, and turning it on restores clipping. Map colors
use softer preview lighting and filmic tone mapping; Neutral restores the original
lighting. No console warnings/errors were observed. Viewport override reset.

The browser is left on Academy in color mode, cutoff25.4m, with P01→P06 shown.
Screenshot `.local/academy-map-colors.png`; neutral comparison
`.local/academy-neutral.png`. Mark the existing Atlas tab as deliverable before
ending the turn. Current owned Atlas server remains PID1290306 at localhost8741.
Backend milestone:8aa6f11; use git log for the final viewer/documentation commit.
See docs/MAP_COLORS.md for exact behavior, import commands and future limitations.

The requested one-map proof is complete. Full textures/layer evaluation and other
map color imports are follow-up work; do not describe this preview as pixel-accurate
game rendering or as color coverage for the entire catalog. Portle and the live
game host were untouched.

## Follow-up — current-view PNG screenshot utility, 2026-11-03 (complete)

User requested a screenshot utility for the current view. Added **Screenshot**
beside the 3D/Top/reset controls. It downloads the map viewport as a PNG at the
existing WebGL drawing-buffer resolution, preserving camera, surface colors,
cutaway, geometry visibility, portal walls, route/all-angle overlays and visible
wall labels. Toolbars/side panels are excluded. Labels hidden in the app are also
hidden in the export. Filenames include the map, 3d/top mode and UTC timestamp.
The screenshot is output from the asset-based viewer, never a map input.

`web/screenshot.js` composites a fresh WebGL frame, matching radial background and
the visible DOM label boxes/text into a temporary 2D canvas. WebGL pixels are
copied synchronously after render; preserveDrawingBuffer remains off. It encodes
PNG using toBlob and downloads via a temporary object URL, revoked after60s.
Capture is entirely browser-local: no uploads, backend changes or dependencies.
Lost graphics contexts, unavailable canvas/encoding and map-loading states are
handled with disabled controls or an error toast. Repeat captures are disabled
while encoding. View tools wrap on narrow screens.

Verification: JS syntax checks passed for web/app.js and web/screenshot.js. Actual
browser downloads were inspected as PNGs: colored3D with labels/route at1635×2499
(2,629,276bytes); neutral top view without labels at1635×2499; mobile top view at
654×932. The 3D image contains geometry, selected labels and route lines rather
than a blank WebGL frame; alpha is fully opaque over the background. At390×844
the Screenshot button fits and the document has no horizontal overflow. No console
warnings/errors were observed. Browser viewport override reset, Academy restored
to3D/color mode with labels, cutoff25.4m and the saved P01→P06 route selections.

The browser automation's download-event wait timed out for a blob download despite
the app succeeding; verified the real output files under the known Downloads
directory instead. A subsequent click confirmed the success toast and re-enabled
button. No alternate browser-control mechanism was used.

Artifacts: `.local/map-screenshot-example.png` is an unmodified copy of the final
utility output; `.local/screenshot-utility-preview.png` shows the app/control.
Original QA downloads remain in `/home/lambchopper67/Downloads/` with prefix
`portal-atlas-Academy-`. Their UTC timestamps fall on Nov4, corresponding to the
user's Nov3 Pacific session. Assets and screenshots remain ignored by Git.

README and in-app Help explain capture. No geometry, route computation, scene data,
Portle or game-host changes. No server restart needed; owned Atlas PID1290306
continues at localhost8741. Existing Atlas browser tab3 marked deliverable.

## Follow-up — portal visibility for manual Portle clues, 2026-11-03

User now wants to author Portle clues manually using Atlas screenshots, and
explicitly authorized changes to both independent repositories. Atlas still reads
game geometry from assets; screenshots are clue outputs, never map inputs.

Added global **Portals** overlay toggle; per-wall visibility checkboxes; Show all,
Hide all and Only selected controls; and a capture-panel multi-select under
**Choose portals for clues** (also accessible on mobile where the left panel is
hidden). These control portal meshes/outlines, labels and connected angle/route
overlay lines. Hidden walls are excluded from viewport picking. The graph and
route costs remain unchanged; this is distinct from Avoid/blocking a route wall.
Actual map mesh geometry is not removed. Per-map hidden IDs are stored separately
in browser localStorage (`portal-atlas-hidden-portals`), with guarded loading.

Browser QA: Academy Hide all gave0/69 visible with0 visible label elements; checking
P01 gave1/69; reload retained1/69; multi-selecting P01/P02 gave2/69; global Portals
off gave0/69. Restored Show all at handoff (69/69). Screenshot utility works with
the selected subset. No console warnings/errors. JavaScript syntax check passed.
Screenshot `.local/portal-visibility-preview.png` shows the one-portal setup.

Current Atlas server remains PID1290306 at localhost8741; no restart needed. No
asset import, geometry change, graph rebuild or live game-host interaction.
Portle's separate manual editor is being verified in its own repository.
