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

Final authoring follow-up: added a **Lines** checkbox to hide angle/route overlay
lines independently while retaining selected portal overlays, and a visible
portal count inside the capture panel (also on mobile). At390×844, the panel
successfully hid all (0/69) and selected P01/P02 (2/69), without horizontal overflow.
Restored Show all and default line visibility. P01→P06 remained4steps/4.5s/78
difficulty with Lines off. Actual architecture and graph/costs are unchanged.
JS syntax check passed; no console warnings/errors. Atlas remains PID1290306.
Portal visibility milestone e642790; use git log for the final capture refinements.
Portle manual editor is now complete at localhost8742/manage, with an empty real
library ready for the user's first six-image set. No Atlas data is read by default
Portle gameplay. Both repos retain independent commits/handoff documentation.

## Follow-up — live selection and saved wall groups, 2026-11-03

Latest user request: easily show/hide groups of portal walls, creating groups by
selecting directly on the live map. Implementation is complete; final responsive
and screenshot QA is in progress at this milestone. No Portle or game-host edits.

Wall groups opens an arena-scoped panel. Select walls on map enables primary
click/tap toggles on portal faces or labels; drag adds visible wall centers inside
the rectangle; Shift-drag removes. Navigation pauses while selecting. Done or
Escape resumes it and opens the group editor. Captured primary gestures prevent
OrbitControls and ordinary route selection from acting on the same events.
Pointer cancellation discards unfinished rectangles. Layer tools tuck away in
selection mode; saved members may also be removed with individual chips.

Selections have Show/Hide/Only these controls. Named groups support the same bulk
actions, load/edit/rename/update, Save as new and delete. Groups may overlap;
show/hide affects actual wall IDs, not independent group layers. Hidden members
remain in groups but cannot be picked until shown. Route start/end/avoidance are
separate. Storage key portal-atlas-wall-groups contains map-to-group arrays;
normalization rejects corrupt records and filters stale/foreign wall IDs.
Gold editing highlights are temporarily removed for synchronous PNG compositing,
then immediately restored; group controls/rectangle are outside captured content.

Validation so far: JS syntax passed; node --test tests/*.test.mjs passed8 tests
(5 colors +3 group state/box tests). Browser: three map label clicks selected3
walls without changing route endpoints; clicking the P01 mesh toggled it off;
dragging (320,800)→(580,980) added9 walls for11 total. Saved Clue example, Hide
gave58/69, Only these gave11/69. Reload retained both group and visibility.
Edited to10 members (removed P46), renamed Clue 1 example, updated. Switching
Academy→Abyss showed no groups/selection; switching back restored the one group.
No console warnings/errors. Current desktop tab3 on Academy; temporary responsive
tab8 at390×844 is still open, to be reset/closed after final QA. Main server is
still owned PID1290306 on8741; files are served directly, no restart needed.

Next: reload responsive tab after the layer-panel selection polish, verify tap,
group actions and no overflow; verify PNG capture while editing; restore useful
desktop state and save proof screenshot; append final results and commit.

Final QA completed: at390×844, live map label taps selected P09/P46. Only these
gave2/69, Hide0/69, Show2/69; no horizontal overflow. Layer tools disappeared
while selecting and returned on Done. Adaptive label decluttering can hide a
nearby unselected label when another wall gains priority; use the wall face or
box selection in that case. Temporary tab8 closed and viewport override reset.

PNG captures while editing and after Done (labels off, identical camera) were
1725×2499. Compared all4,310,775pixels:191 differed by at most1 RGB level, with
zero pixels differing by more than1. This confirms editing gold was removed from
the exported frame. Copies: .local/group-editing-capture.png and comparison
.local/group-capture-diff.png. Python3's Pillow is available system-wide; it is
not installed in the Atlas venv. No dependency was added.

Desktop Academy restored to69/69 portals, Labels/Lines on, 3D/color mode, cutoff
25.4m. P01→P06 remains4steps/4.5s/peak78/142m. Example saved group Clue 1 example
has10walls, available for demonstration; current selection holds those members.
Selection mode finished; group panel open. Browser tab3 marked deliverable.
Screenshot .local/wall-groups-preview.png shows the group with gold live-selection
highlights before Done. The in-app screenshot surface sometimes lags one UI frame;
DOM inspection confirmed the final non-editing state. No app console warnings or
errors. Fixed left-list gold styles to clear immediately when selection ends.

Box selection operates on projected centers of enabled portal overlays within the
camera frustum, including walls occluded by geometry. It is a selection-through
tool; rendering/geometry occlusion does not filter the box. Hidden portal IDs and
master Portals off are excluded. Primary clicks target the nearest portal mesh,
as the existing viewer did. README documents the selection-through behavior.

Commands: Node --check web/app.js passed; node --test tests/*.test.mjs passed8.
Frontend-only changes; Python routing/asset code and datasets are untouched, so
their previously passing48 tests were not repeated. No outstanding work for this
request. No server restart or game-host operations; Atlas PID1290306 on8741 stays
running. Portle remains independent on8742 with its empty manual clue library.

Final reload/selection cleanup check: selected10, Done left editing=false and
left-list group highlights=0, while retaining10 selected members and69/69 shown.
git diff --check passed. Browser automation had transient frame/evaluation delays
during reload; a fresh read confirmed Loading hidden and normal app state before
continuing. These were automation delays, not app console errors.

## Active follow-up — all-map asset color rollout, 2026-11-03

User requested color support for all other maps. Work is in progress. Preserve
the same representative parameter-color qualification; no screenshot sampling,
guessed asset-name colors, texture evaluation or live game-host operations.

Added --all-arenas and --refresh to tools/import_colors.py. Batch includes25
already-imported standalone arena/training datasets and excludes Ozone/Ozone
Graffiti shared sublevel libraries. It holds the existing import lock, limits
reader processors to2, validates a staging sidecar before atomic publication,
reuses validated current outputs, records per-map progress/failures in ignored
data/color-import-report.json and continues after individual failures. Failed
validation retains the last published sidecar and saves diagnostic JSON under
.local/<map>-colors-rejected.json. Per-map reader logs remain in .local/.

tools/audit_colors.py checks map/revision, asset/parameter provenance, finite
linear RGB, mesh buffers/LODs/section coverage, overrides and export errors. It
measures colored triangles across visible instances, including per-component
overrides and actual simplified proxy counts (not full source render counts).
Audit writes data/color-validation-report.json. UI now reports this percentage.

Initial all-map pass exposed landscape heightfields being loaded as static
meshes; it was intentionally interrupted while Erosion ran to improve the
reader. Owned wrapper PID29239 was verified by cwd/cmdline before SIGINT; its
owned reader exited and no import remained before rebuilding. Completed sidecars
were retained. No geometry/graph inputs were changed. Baseline hashes for all25
scenes are in .local/color-rollout-scene-baseline.json.

ColorExporter now reads native mesh.Materials directly, avoiding massive JSON
serialization of all vertex/index LODs. Academy's459 mesh slot arrays and material
records matched the original pilot exactly after this change. Terrain uses its
serialized component override or LOD-selected landscape material instance as a
single representative shader color; terrain layer masks/textures remain excluded.
Single-material static-mesh proxies can now use their sole source material on
the collision hull; ambiguous multi-material proxies stay neutral. Sidecar
sections match the actual proxy buffer. Browser accepts validated proxy sections.

Built with CUE4PARSE_SKIP_NATIVE=1 DOTNET_PROCESSOR_COUNT=2 .tools/dotnet/dotnet
build tools/AssetReader -c Release -m:2 --no-restore. Success, existing upstream
Bcl.Memory9.0.0 warning and pre-existing FeatureExporter nullable warning remain;
reader directly references patched9.0.14 as documented earlier. Never rebuild
while an AssetReader process is running.

Current verification pilot command (exec session75974):
`.venv/bin/python tools/import_colors.py MAP_Academy MAP_Bypass MAP_Erosion MAP_Karman_Station --refresh > .local/colors-upgrade.log 2>&1`
Academy passed69.0%; Bypass now passed63.5% with landscape handling. Erosion was
at800/1108 appearance meshes when last inspected; processor use about1core and
RSS1GB. Wait for completion, inspect/fix any rejected outputs, then run the full
25-map refresh with the improved reader. Existing first-pass report has partial
coverage values from before corrected proxy denominator; refresh all before
publishing final coverage table. Five new audit/batch tests and9 Node tests pass.
Added a real-asset rollout test covering every ready standalone map; run it after
all imports exist. Full Python tests and final browser QA still required.

Atlas localhost8741 was stopped on this resumed host (old PID1290306 is stale).
Start this repo's local server for UI verification and record its new owned PID.
Do not signal the old PID. Portle is user-managed and must not be restarted or
modified. No subagents were spawned.

Reader scaling follow-up: after native mesh slots were optimized, the Erosion
pilot still expanded native component instance arrays while obtaining overrides.
Verified/stopped owned pilot wrapper30950 (session75974) before rebuilding.
Added PropertiesOnly(UObject), which serializes property tags with the same JSON
converters but omits unrelated native render/instance data. Academy's complete
materials, meshes and components tables still match the original pilot exactly.
Final full refresh is now running in exec session38500:
`.venv/bin/python tools/import_colors.py --all-arenas --refresh > .local/colors-rollout-final.log 2>&1`
Completed Abyss, Academy, Bypass, Containment, Core and Eden without validation
errors; Erosion was processing when last checked. No reader rebuild until done.

Atlas restarted in foreground exec session10355, PID32297, onlocalhost8741;
.local/server.pid updated. Initial shell-background nohup launch did not survive
the command; this server is the one confirmed HTTP200. Keep it running at handoff.
Current browser inventory changed after app/host restart: browser2 tabs1/2 are
Atlas, tab3 Portle/manage, tab4 Discord docs. Old bindings/tab numbers are stale.
Selecting Atlas tab2 was rejected by browser security because its failed-load
internal error page has a disallowed protocol. Do not work around this with other
browser surfaces. An async user question requests refreshing the existing Atlas
tab and replying ready; continue import/audit work while awaiting that action.
Browser QA is pending a genuine refreshed http document, not permission to bypass
the browser restriction.

Definitive scaling fix: cached loaded IPackage objects by canonical archive path.
Without it, embedded landscape material references repeatedly reparsed the same
94MB Erosion level. Verified/stopped owned wrapper32190 (session38500) before the
final reader rebuild. Pilot Erosion + Karman Station (session68082) then passed
in13.9s and6.1s respectively, with0 reader/audit errors; Erosion238/1714 material
colors,10.1% rendered-triangle coverage; Karman54/144,12.0%. Package count is now
recorded in each reader report. Properties-only/native-slot optimizations remain
and Academy tables still match the original pilot.

Full25-map completion batch is running in exec session50831:
`.venv/bin/python tools/import_colors.py --all-arenas > .local/colors-rollout-complete.log 2>&1`
It reuses the eight validated outputs and imports remaining scenes. Do not
rebuild until it exits. Afterward audit all25, verify baseline scene hashes,
exercise all color endpoints, run full Python/Node tests and document coverage.

User replied Ready after opening a NEW live Atlas tab5 in browser2. A subsequent
attempt on old tab1 was still rejected (its actual page is data: error HTML).
Inventory then identified the human-opened tab5 with valid http URL/title; bound
it as verifiedAtlasTab. Old blocked error tabs1/2 were left untouched. This is a
new allowed document following the user's action, not a bypass of blocked pages.
Browser QA on tab5: Core color mode reports81.1%; Neutral survives reload; switching
back to Map colors and selecting Bypass reports63.5%. Geometry rendered, with
colored proxy surfaces visible on Core. Remaining GUI cutaway/screenshot checks
and final proof screenshot are pending. Atlas server is still PID32297/session10355.

## All-map color rollout — complete

All25 standalone arena/training datasets now have current validated appearance
sidecars. Completion batch session50831 exited0. Every map passed the independent
tools/audit_colors.py audit with no mesh/level/material exceptions. Total4199
recovered material records across map exports (shared assets counted per map).
Rendered mesh triangle coverage ranges0.1% (Training) to85.4% (Terra13). This is
still a representative parameter-color preview; texture-heavy maps such as
Training/Abyss remain mostly neutral. No guessed colors or image sampling added.
Full per-map table and qualifications are in docs/MAP_COLORS.md.

Final verification:
- `.venv/bin/python tools/audit_colors.py` passed25/25, report in ignored
  data/color-validation-report.json.
- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m unittest discover
  -s tests -v` passed54 tests in2.933s; .local/tests-colors-all.log.
- Node --test tests/*.test.mjs passed9; Node --check web/app.js passed.
- Second `tools/import_colors.py --all-arenas` run validated/reused25/25 outputs,
  invoked no reader and exited0; .local/colors-resume-check.log.
- All25 scene/graph JSON SHA256 values exactly match the pre-rollout baseline.
- Bounded two-worker HTTP sweep returned available=true/current revisions and
  coverage for all25 /api/colors/<map> endpoints.

Browser QA on the human-opened valid HTTP Atlas tab5: Core81.1% color view; Neutral
persisted through reload; Bypass63.5% with visible purple/red foliage, landscape
and architecture. Checked a20m cutoff, Cutaway off/on and top/orbit switching.
Restored Bypass's prior17m cutoff and3D view. Screenshot utility displayed the
success toast and re-enabled its button; browser download-event API timed out
without exposing a saved file path, so no new independent PNG-file inspection
is claimed. Native UI proof saved .local/all-map-colors-preview.png.
At390×844, coverage label fits and document has no horizontal overflow. Override
reset; user tab5 marked deliverable. No console warnings/errors. Old error-page
tabs1/2 and Portle tab3 were left untouched.

Atlas continues at localhost8741, owned PID32297 in foreground exec session10355,
tracked by .local/server.pid. Keep running; verify identity before any signal.
No asset import jobs remain. Proprietary sidecars, logs and screenshots are
ignored. No game installation/host, route costs/graphs, Portle data or bot changes.
No required work remains for this request. Future fidelity work is texture/UV
support, actual terrain-layer evaluation and transparency; retain provenance and
current neutral fallback until those inputs are supported.

## Relaunch for screenshot preparation — 2026-11-04

User requested reopening Atlas and the Portle clue editor to prepare screenshots.
Atlas was no longer listening on8741; launched `./run.sh` in exec session49751.
Current owned listener is PID372689, `.venv/bin/python -m server`, bound only to
127.0.0.1:8741. Updated ignored .local/server.pid after checking process identity.
This supersedes old PID32297/session10355 notes; verify identity before signals.

HTTP root returned200. Reloaded the valid user Atlas browser2/tab5 at
/#map=MAP_Terra13; map renders, Screenshot button is enabled, color coverage85.4%.
Portle preview/editor was still running on8742, PID213145, and /manage returned200.
Opened fresh editor tab8, selected Terra13 to match Atlas and left both tabs as
deliverables. No portal visibility, camera, asset data, clue uploads/publication
or Discord bot changes were made. Old error tabs were untouched. Native UI proofs
saved under ignored .local/relaunch-atlas.png and Portle/.local/relaunch-editor.png.
No code changes/tests required for this operational relaunch. Both servers remain
running for the user; editor URL is http://127.0.0.1:8742/manage.

## Balanced random portal groups for Portle — 2026-11-09

User requested six random equally sized groups, refreshable when the distribution
is undesirable, with each portal in exactly one group. Added Random Portle groups
at the top of the existing Wall groups panel. Create 6 random groups / Reshuffle
6 groups shuffles all current scene.nodes IDs (including hidden walls), then
partitions them into six disjoint arrays. Counts are exactly equal when divisible
by6; otherwise sizes differ by at most1, with remainder walls in the first groups.
Fewer than6 walls yields empty trailing groups, with empty isolate buttons disabled.
Generation immediately shows group1. Only this isolates a group; Through here
isolates groups1–N, allowing progressively more portals in the six screenshots.
These visibility choices preserve camera/cutaway, routes and underlying assets.

Random partitions have their own map-scoped localStorage key,
portal-atlas-clue-groups, separate from manual portal-atlas-wall-groups. Creation
and reshuffle replace only that arena's random partition. Existing manual named
selections can overlap and remain unchanged; random groups cannot overlap. A
strict saved-partition validator rejects corrupt data, changed/missing/foreign
wall IDs, duplicate membership and unbalanced sizes, so a stale set must be
regenerated. Storage failure keeps the previous set and gives an error toast.
The Wall groups badge counts manual plus random groups. UI shows group sizes and
currently visible wall counts, with active visibility buttons. README and in-app
help explain the capture workflow and remainder behavior. No Portle changes,
automatic screenshots/uploads, asset extraction or graph modifications.

Validation:
- Node --test tests/*.test.mjs passed13 tests (four new partition/reshuffle/storage/
  cumulative-visibility tests). Deterministic checks cover counts0–401, every
  remainder, no duplicates/omissions, source immutability, stale saved groups and
  progressively nested visibility. Existing manual group and color tests pass.
- OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m unittest discover
  -s tests -q passed54 tests in5.249s. The MAP_Test stale-revision output is the
  expected negative audit fixture; the suite endedOK.
- Node --check web/app.js and web/portal-groups.js; git diff --check passed.
- Browser2 fresh tab11 /#map=MAP_Terra13:112 walls split19/19/19/19/18/18.
  Clicked Only this on all six groups and read actual wall visibility checkboxes:
  total112, unique112. Through here3 showed57/112; through6 showed112/112.
  Reshuffle changed group1, preserved all coverage counts, and reload retained
  identical membership. Map switching to Academy showed no Terra groups. Generated
  Academy12/12/12/11/11/11 while its existing manual Clue1 example stayed10walls.
  Returning to Terra restored its previous partition. Final reload also passed.
- Default1280px viewport had no horizontal overflow; panel remains276px wide and
  scrolls to later groups/manual controls. No viewport overrides were applied.
  No browser console errors/warnings. Screenshot .local/random-portle-groups.png
  shows the final Terra13 panel/group1; tab11 marked deliverable.

Atlas was not listening before QA. Started ./run.sh, owned PID30047 / exec
session96060, on127.0.0.1:8741 and updated .local/server.pid after identity checks.
Leave it running for capture; verify process identity before any future signal.
New random groups and current visibility remain saved for Terra13 and Academy.
No imports are running. Old browser error tabs, Portle editor/bot/hosting, game
installation and SplitgateHost were untouched. Commit this milestone locally;
Atlas remains independent from the Portle GitHub repository and is not published.

## Dought display name and batch capture feasibility — 2026-11-09

User asked whether every map can be captured programmatically from random camera
angles, and requested renaming Erosion to Dought (spelling as explicitly given).
Checked existing fitView, bounds, loadScene and captureMapView paths: sequential
batch capture is feasible by loading each ready scene, waiting until geometry
finishes, choosing bounded azimuth/elevation/distance around its wall bounds and
capturing the real renderer. Six random portal groups can provide nested clues.
A future tool should allow repeatable seeds, constrain framing, hide labels/routes,
write separate reviewable PNGs and avoid automatically publishing Portle clues.
Random angles cannot guarantee unobstructed/interesting views. No batch capture
runner or random-angle control was implemented; this part was a feasibility
question. Existing manual screenshot workflow remains available.

Implemented server presentation override MAP_Erosion→Dought for arena listings
and scene responses, without modifying raw scene files, root packages, IDs or
revisions. Existing map search accepts both displayed name and internal ID, so
searching Erosion still finds Dought. Screenshot filenames now use scene.name,
so new captures use Dought. Stable IDs preserve saved groups, visibility, route
references and appearance sidecars. Portle's independent repo also updates its
answer roster and future legacy imports, retaining Erosion as a guess alias.
Historical frozen Portle snapshot names are not rewritten.

Validation:54 Python tests passed in2.708s;13 Node tests passed; web/app.js syntax
and whitespace checks passed. Live /api/maps and /api/maps/MAP_Erosion both show
Dought, retaining identical scene revision/nodes/edges. Raw scene SHA256 remained
bdbc95f6ef0259e9b71e6f883844d59c5d5f969036339fae532394242fbd41cf.
Browser2/tab11: Dought search found447walls/1808edges; clicked map, verified title,
completed render and enabled Screenshot; color coverage10.1%, no console errors.
Native proof .local/dought-map-name.png; tab11 left on Dought and marked deliverable.

API code required restarting the owned Atlas listener. Verified PID30047/cwd and
python -m server before SIGTERM; relaunched ./run.sh in exec session46138, current
PID43818 onlocalhost8741, updated .local/server.pid after identity checks. No
imports, source/game changes, clue publications or Discord operations. Commit
Atlas locally only, independently of Portle's GitHub update.

## Batch clue capture — implementation milestone, 2026-11-09

User explicitly requested implementing the batch tool after the feasibility
assessment. Added Batch clues dialog: all25 imported standalone maps, current
map, or checked subset; six progressive1–N or disjoint groups; random view per
clue or one view per map; output1280x800/1600x1000/1920x1080; repeatable seed and
New seed; progress, cancellation, ZIP download and error report. PNGs/manifest
stay local in browser memory until download; nothing publishes into Portle.

web/batch-capture.js provides separate seeded group/camera streams per map,
full-aperture bounding-sphere/frustum camera placement at35–65degree elevations,
and a stored-entry ZIP writer with CRC32 and384MiB cap. PNGs are already compressed.
Manifest records source/map revision, group IDs, six camera poses, visibility,
saved cutoff, color coverage and errors. Groups/images do not replace saved
manual/random groups. Sequential maps use two mesh loaders. Invalid/missing mesh
loads skip the map; unfinished maps are discarded on cancellation while completed
maps remain in the ZIP. Frame capture hides labels/lines/grid/editing highlights,
forces geometry/portals visible and uses explicit output resolution.

web/batch-ui.js orchestrates the modal/run; app.js adapter snapshots/restores
original map, camera, render dimensions/pixel ratio, layer flags, cutoff/surfaces,
portal visibility, route and selection/group UI. loadScene has batch error returns,
no batch hash/route restoration, and early exits for cancelled mesh workers.
Keyboard camera shortcuts and ordinary map changes are blocked during the modal
run. Existing map source files and all localStorage settings remain unchanged.
Current-map restoration can reuse already-loaded geometry to avoid another load.

Validation at this milestone:17 Node tests passed, including deterministic seeds,
map-order independence, nested/disjoint membership, fixed camera, all portal-box
corners fitting portrait/landscape frusta and ZIP header/CRC/path/size checks.
Python zipfile independently validated ZIP output. Existing54 Python tests passed
in2.836s. Browser2/tab11 captured six real Dought PNGs,1280x800, all different,
without embedded metadata. Actual downloaded ZIP is in the user's Downloads as
portal-atlas-clues-portle-batch-qa-2026-11-09.zip; its CRC/integrity and manifest
passed Python validation.447 walls group75/75/75/74/74/74; cumulative75/150/225/
299/373/447. No errors. Before/after DOM checks showed identical original map,
portal visibility, labels/lines, cutoff and canvas dimensions. Unmodified PNG
copies for inspection: .local/batch-qa-dought-01.png and -06.png. Browser's download
event API timed out, but the normal UI link did save the exact named file into
Downloads, which was read as a task output artifact (no browser profile access).

Pending final QA: current code was reloaded after accessible labels and same-map
restore optimization. Test cancellation, selected-map mode and an all-map run;
inspect outputs and save final UI proof, then document results and commit final
milestone. Atlas listener remains owned PID43818/session46138 at127.0.0.1:8741;
no restart required for these static frontend changes. No asset import workers,
Portle/Discord/hosting changes or public uploads. Keep proprietary outputs ignored.

## Batch capture — final verification, 2026-11-09

Implementation committed at cbca2f6. Completed a real all-map browser run with
seed portle-all-maps-2026-11-09, default 1280x800, separate random camera per clue
and progressive groups. Finished 25/25 maps and 150 screenshots without errors.
Downloaded via the normal Download ZIP link to:
/home/lambchopper67/Downloads/portal-atlas-clues-portle-all-maps-2026-11-09.zip
(108.5 MiB). Python zipfile.testzip passed; Pillow decoded all 150 PNGs, all
1280x800 with no embedded metadata and 150 distinct SHA256 hashes. Manifest
membership checks confirmed all six groups balanced/exclusive with exact portal
coverage, and every clue's visible IDs equal the corresponding prefix union.
All 25 original scene hashes match .local/batch-source-baseline.json. Saved
manifest copy: .local/batch-all-maps-manifest.json. Output stays ignored/local.

Cancellation QA: started all-map run, cancelled during first load, got Cancelled
0/25 maps and 0 screenshots; original Dought map/visibility/labels/lines/cutoff/
canvas dimensions restored. The successful Dought and all-map runs restored the
same baseline too. Selected-map UI checked with 25, one (Dought) and zero checked
maps: summaries 150/6/0 images and Start disabled for zero. Browser console had
no errors. Proof of completed full run: .local/batch-capture-complete.png.

Final polish explicitly keeps OrbitControls disabled when group mode resets
during a batch, fixes singular map summary and README spacing. Reloaded latest
frontend in browser2/tab11 after these edits. Tests remain 17 Node + 54 Python
passing; JS syntax/whitespace checks pass. No extra full-map run needed for the
small control-lock/text changes. Atlas remains running at127.0.0.1:8741 with owned
PID43818/session46138; leave it available. No Portle, Discord, hosted bot, game,
source asset or SplitgateHost changes. No remaining required implementation work.

Use Batch clues below the viewer toolbar, select maps/settings, choose New seed
for another distribution, Start batch, then Download ZIP. Review images before
manually adding them through the Portle clue editor: random framing fits portal
apertures but cannot guarantee attractive or unobstructed clue views. Current
cutoff/surface settings are used; saved manual groups are preserved. Archive
limit384MiB; smaller subsets/resolutions are available if reached. Commit final
verification locally only; this Atlas repo has no remote and is not published.

## Portal-only batch regeneration — 2026-11-09

User requested regenerated clues with geometry off, portals on, labels/lines/all
angles/cutaway off, plus a data folder for the hosted Portle bot. Added explicit
Include geometry and Enable cutaway checkboxes to Batch clues, both default off.
Other clue layers remain fixed as requested. The selected settings are applied
before each map loads and recorded in top-level settings.layers and every map's
layers. Saved viewer settings are restored afterward. README reflects defaults.

Browser2/tab11 completed all25 maps/150 PNGs with seed
portle-portals-only-2026-11-09,1280x800, progressive groups/random angle per clue.
Normal Download ZIP saved the raw batch in Downloads as
portal-atlas-clues-portle-portals-only-2026-11-09.zip. Manifest confirms requested
flags, cutoffHeight null, no errors/cancellation. A decoded Academy clue6 sample
shows only portal apertures on the viewer background: ignored
.local/portals-only-academy-06.png. Completion proof:
.local/batch-portals-only-complete.png. Source SHA256 baseline matches all25 scenes.
Latest JS syntax and all4 batch-specific Node tests passed; diff check passed.

Portle packaging runs separately via ignored .local/package-portal-batch.py in
the Portle repo. It converts real captured PNGs through ClueLibrary into an
isolated data/clues folder, publishing the23 supported answer sets; Training and
HangmanR3 are excluded by the bot roster. It preserves old local images for frozen
rounds, never opens live scores or .env, and does not modify the source library.
See Portle handoff for final archive validation/output path. No upload or live bot
operation is part of this request. Atlas stays running at127.0.0.1:8741; no restart
was needed. Keep all proprietary output artifacts ignored/outside Git.

## Growing clue groups — implementation milestone, 2026-11-17

User requested replacing even batch portal groups with progressively larger
additions, minimum four portals first; example50 portals =4/5/7/9/11/14. Interpreted
as disjoint new additions with cumulative screenshots4/9/16/25/36/50, stated to
the user before capture. Added progressiveGroupSizes to batch-capture.js: baseline
four in each group, remaining N-24 weighted1/3/5/7/10 across groups2–6 with largest
remainder rounding. Group1 stays exactly4, all walls appear exactly once, later
groups are nondecreasing. For tiny maps below24, first min(4,N), remainder evenly
among five groups; cannot satisfy six nondecreasing groups starting4. All23 Portle
answer maps exceed that limit. Existing manual Wall groups stay even/unchanged.

Batch dialog Group sizes defaults to Growing groups; Even groups retains prior
behavior. settings.distribution records the choice; seeded wall shuffle and
camera streams stay independent. README documents incremental vs visible counts.
18 Node tests passed, including invariants for N=0..1000, exact requested example,
cumulative/nested/disjoint membership, legacy-even and camera/ZIP regressions.
Latest batch5 tests, batch-ui syntax and whitespace checks passed after refactor.

Previous Atlas listener was no longer running, so started ./run.sh --port 8741,
session19997, verified listening PID1386730.
Browser2 fresh tab1 atlocalhost8741 is capturing all25 maps/150 screenshots with
seed portle-progressive-2026-11-17,1280x800,cumulative,growing groups,random angle
per clue; geometry/labels/lines/all angles/cutaway off, portals on. No console
errors so far; do not refresh until completed. Raw output expected in Downloads
as portal-atlas-clues-portle-progressive-2026-11-17.zip.

Pending: finish capture/download, validate groups and all PNGs, create uploadable
Portle library and named PNG review ZIP using ignored Portle script
.local/package-progressive-batch-2026-11-17.py (syntax passed). It uses prior
Nov9 export images plus local originals for historical retention, excludes two
non-answer maps, normalizes/publishes only into an isolated Nov17 output folder,
exercises all23 maps using temporary scores, and preserves existing libraries.
No hosted bot, Discord, production scores, tokens, game or host workers touched.

### Browser download recovery — 2026-11-17

First progressive run finished25/25 maps/150 PNGs with no errors. Browser normal
Download ZIP click produced no file in Downloads; documented downloadMedia hung
and reset its kernel, and waitForEvent(download) timed out. PageAssets inventory
did not expose the blob archive. Never used raw browser sockets, injected JS,
profiles or browser storage. Screenshot of that completed run was saved, but raw
ZIP was not accessible. Added a supported user-facing Save ZIP locally option,
then repeated the same deterministic batch to produce a usable artifact.

New server/captures.py streams bounded ZIPs to private unique ignored
.local/captures/capture-<uuid>.zip paths. Validates ZIP entries, path allowlist,
manifest type/version, entry count, compressed/uncompressed size caps; deletes
partial/invalid uploads. API requires local Host, exact same Origin and ZIP
Content-Type; output files0600, directories0700, no overwrite/unpack/public serve.
batch-ui retains the actual generated Blob and sends it only when Save ZIP locally
is clicked; shows the saved path, blocks overlapping runs/saves. Normal Download
ZIP remains available. README documents this fallback.

57 Python tests passed in3.666s (expected stale-revision negative fixture prints
FAILED inside its passing test). New tests cover byte-preserving private saves,
non-overwrite, incomplete/bad/path-traversal cleanup, size limits and HTTP origin
checks. Batch-ui syntax passes. Verified owned PID1386730/cwd before terminating
and restarting Atlas for new backend: ./run.sh --port 8741, session1366, current
verified PID1414907, .local/server.pid set.
Browser2/tab1 was reloaded and second identical all-map batch started; do not
refresh until it finishes. Next: Save ZIP locally, copy returned local archive to
the expected Downloads filename and run the prepared Portle packaging script.

### Progressive captures — final verification, 2026-11-17

Second all-map run completed25/25 maps and150 images with no errors. Save ZIP
locally succeeded through normal UI and returned:
.local/captures/capture-6e1ece653d32447a9d333a846a4c907e.zip
Copied this exact artifact to /home/lambchopper67/Downloads/
portal-atlas-clues-portle-progressive-2026-11-17.zip for packaging. PNGs1280x800,
all150 unique, no metadata. All25 manifests have the requested portal-only layer
flags/cutoff null; groups cover every wall once and cumulative visibility is
correct. All23 Portle maps start4, groups nondecreasing, final clue covers all.
Actual50-portal Training map matches exact4/5/7/9/11/14 additions and4/9/16/25/36/50
visible counts. Academy69:4/6/9/13/16/21 additions,4/10/19/32/48/69 visible. Dought447:
4/20/53/85/118/167 additions,4/24/77/162/280/447 visible. HangmanR3 tiny-map fallback
is outside Portle's answer list. All25 source scene hashes remained unchanged.

Completion proof .local/batch-progressive-complete-2026-11-17.png shows selected
growing groups, completed progress and saved file path. Unmodified extracted
Academy clues1/6 at .local/progressive-academy-01-2026-11-17.png and -06-.png;
viewed clue1: four apertures only, no geometry/labels/lines/grid/cutaway.
Portle packaging passed for23 maps/138 new clues, retained162 historical files,
300 PNGs total,58.17MiB host-ready ZIP plus a separate138-PNG named review ZIP.
Detailed outputs, hashes and upload directions are in Portle handoff. Both
original libraries and installed game/source data preserved; no host uploads,
Discord calls, score DB writes or public publication. Browser2/tab1 is marked
deliverable with completed run; Atlas PID1414907/session1366 left running.
Final tests18 Node +57 Python pass; no remaining required work.

## Separate Simulation/takedown maps — 2026-11-17

User clarified that the upload index/files must include only current clues,
discarding old images, and asked about takedown maps. Verified prior index already
referenced only138 current PNGs; historical162 were extra ZIP files. Created an
initial23-map new-only export, then captured six additional Simulation maps and
built a superseding29-map new-only host package (see Portle handoff).

Asset index revealed six independent roots in MAP_Simulation bundle: Anomaly,
Charlie, Divide, Faceoff, Hectic, Moshpit. Previous all-arenas importer excluded
this multi-root bundle. Added server/map_variants.py registry mapping stable
MAP_Simulation_<Name> scene IDs to parent feature/explicit root. Expanded API/CLI
map inventories expose six maps instead of ambiguous MAP_Simulation container.
compile_scene --scene-id writes separate files while loading parent's extraction;
checks scene ID matches its registered feature/root before reading/writing.
source.feature preserves bundle identity; rootPackage/source.levels remain actual
cooked sources. Import API and tools/import_maps.py handle parent extraction and
explicit root/scene ID. finalize_scene CLI reads source.feature for variants.
No roots are merged and no original scene is overwritten. README updated31 maps.

Read-only asset export under import.lock/2 .NET CPUs succeeded (284 walls,22
packages,6597 components,91 meshes,0 extraction errors). Command was existing
AssetReader export-feature MAP_Simulation data/extracted with standard local
key/mapping file env paths and bounded CPU settings; log ignored
.local/simulation-export-2026-11-17.log. Then ran:
.venv/bin/python tools/import_maps.py MAP_Simulation_Anomaly MAP_Simulation_Charlie MAP_Simulation_Divide MAP_Simulation_Faceoff MAP_Simulation_Hectic MAP_Simulation_Moshpit
All ready:39/36/30/50/72/57 walls;154/124/54/238/374/289 edges;geometryUsable true,
2/3/3/2/3/3 active levels. Same6 IDs through tools/import_colors.py succeeded;
representative color coverage5.4/5.5/4.8/4.5/4.5/5.0%, unresolved surfaces neutral.
Original25 scene SHA256 baseline unchanged. All new derived data stays ignored.

Verified owned PID1414907/cwd before SIGTERM, restarted ./run.sh --port 8741 for
API variant inventory: current PID1438385/session36482, .local/server.pid updated.
No host/game workers touched. Browser2/tab1 reloaded, selected only the6 new maps,
seed portle-simulation-progressive-2026-11-17,1280x800,progressive cumulative four
first/random view per clue; portals on,geometry/labels/lines/all angles/cutaway off.
Finished6/6 maps/36 images, no failures or browser errors. Save ZIP locally wrote
.local/captures/capture-514d991796d94ee78fc6670df0baa842.zip (21071114 bytes).
Proof .local/takedown-capture-complete-2026-11-17.png; tab marked deliverable, server
left running. Viewed actual Faceoff clue6 in output package: portals only.

60 Python tests passed in2.831s, including new inventory, root isolation on all6
real scenes and guard against overwriting an unrelated map ID. Expected stale
color revision fixture prints FAILED inside a passing test. Whitespace checks
passed. Portle package validates all29 rounds/dropdown pages offline; no remote
upload, Discord calls, token access, production score changes or public assets.

## Dynamic first-clue portal count — 2026-11-19

User explicitly superseded the fixed-four first clue: portal counts must be
dynamic. Updated web/batch-capture.js progressiveGroupSizes to reserve one wall
per each of six groups, then apportion N-6 walls with weights1/2/3/4/5/6 using
largest-remainder rounding (ties favor later groups). The first group now scales
approximately as1+(N-6)/21. All groups are positive/nondecreasing for N>=6 and
cover each wall exactly once. For N<6, reveal one wall per initial clue with
empty trailing groups. Six clues remain fixed; seeded shuffle/camera independence,
even groups and existing saved manual groups are preserved.

Examples:30 walls adds2/3/4/6/7/8;50 adds3/5/7/9/12/14, visible3/8/15/24/36/50;
447 adds22/43/64/85/106/127. Updated batch dialog label and README to remove the
four-wall promise. Portle's separate manual-clue guide documents the new policy.
Old PNGs, published sets and archived Nov17 packaging scripts remain unchanged;
recapture/republish is required to use these counts in gameplay. Do not reuse
old one-off package validators that explicitly require four walls first.

Validation: node --test --test-isolation=none --test-reporter=tap tests/*.test.mjs
passed18 tests using the bundled Node path above. Direct in-process isolation was
used to observe every subtest rather than the sandbox's file-only worker output.
Tests sweep N=0..1000 for exact coverage, integer/nonnegative counts, positive
nondecreasing groups for N>=6, dynamic first-clue rounding, and tiny-map behavior;
existing nested/disjoint memberships, deterministic seeds, camera/ZIP/color/group
tests pass. node --check web/batch-capture.js and git diff --check pass.
Offline sizes validated against all29 available Portle map scenes; ignored
.local/dynamic-clue-counts-2026-11-19.json records additions/cumulative counts.
Outskirts still lacks a source scene. No source assets, screenshots, clue library,
scores, credentials, live server/browser or game-host processes were changed.
Static frontend changes apply after refreshing Atlas; no backend restart needed.
No capture regeneration or upload was requested/performed in this turn.
