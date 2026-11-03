# Handoff — 2026-11-03

## Authorized scope

Build a local web app from installed game assets. Portal walls are nodes; portal
placement angles and movement are directed edges with time/difficulty costs.
Create an independent repo, commit milestones, maintain handoffs, finish the app.
No videos/screenshots as map input; no deployment. Never touch SplitgateHost or
its live workers. Browser QA screenshots are only verification of our app.

## Repository and runtime

- Repo: /home/lambchopper67/Documents/ChatGPT/Splitgate/PortalAtlas
- Branch: codex/portal-atlas; no remote. Last initial viewer commit 6d7c5d4.
- Run `./run.sh`; local app http://127.0.0.1:8741. Python .venv installed.
- Node: /home/lambchopper67/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
- CUE4Parse pinned d3f153e1aac51808b3d5e7d23c1451fcc70bae85 in ignored
  .tools/CUE4Parse, .NET SDK10.0.403 in .tools/dotnet.
- Build: `CUE4PARSE_SKIP_NATIVE=1 DOTNET_PROCESSOR_COUNT=2 .tools/dotnet/dotnet build tools/AssetReader -c Release -m:2`
- Tests: `.venv/bin/python -m unittest discover -s tests -v` (29 pass).
- Keep OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 for compilers.

## Asset provenance and recovery

Source immutable Docker image splitgate-host:private-game-payload SHA256
2a8c855455249cf97a452345047e67b7f2a8c66c695784d891b6be13f8d61399.
Copied /game/PortalWars2/Content/Paks into ignored data/install/Paks (35.6GiB).
Shipping.exe SHA256 619e4753e2f68c721764a19afe61b01daee723beaa946ef94ec6bb4e0c7c5747.
Separate stopped snapshot container portal-atlas-assets can be removed at finish.
Do not operate any running game container.

`tools/extract_key.py` statically decodes the guarded callback and wrapper;
secret remains data/key.txt (ignored). GAME_Splitgate2 mounts 215,239 files.
data/maps-index.json indexes 1,794 map packages across 34 feature namespaces.

No .usmap is supplied. `tools/reflection_emulator.py` uses isolated Unicorn
emulation of bounded static helpers, intercepting FName; never runs the PE
entrypoint or calls host OS APIs. `tools/native_metadata.py` and
`tools/build_mappings.py` recover 14,358 native type schemas and 2,431 enums.
52 rejected schemas retained in reports; essential geometry schemas validated.
Mappings and overlays stay ignored in data/. Some nongeometry camera warnings
remain visible. Setup scripts reproduce dependencies, key, mappings, and index.

## Implemented

- C# reader exports full feature packages, portal actors/root transforms,
  mesh buffers/body setups, conventional/instanced/FastGeo static components.
- Python compiler follows always-loaded streaming and WorldPartition cells,
  builds portal apertures, transformed collision proxies, directed edges.
- Shared mesh BVHs plus instance TLAS avoid expanding millions of triangles.
  Uses simple convex/box collision and render fallback; skips NoCollision.
  Large-map overview uses actual asset collision hulls for manageable rendering.
- Local web server with confined asset APIs and background allowlisted imports.
- Three.js 3D/top/cutaway viewer, wall picking/list, directed graph, route
  objectives, blocked walls, difficulty/movement filters, save and JSON export.
- Dijkstra respects wall face continuity and launch-wall arrival state.
- Base walking speed5.4m/s, sprint multiplier1.5, agentradius.45m/height2m/
  step.3m recovered from actual assets/config in data/movement-model.json.
  Gravity/jump/placement timings remain explicit estimates; mode overrides not
  resolved. Routes are geometric candidates, not measured gameplay guarantees.
- 29 geometry/routing/HTTP/source tests. Initial Academy browser route/save,
  top/cutaway QA passed. Final all-map and import/error/export QA still pending.

## Active jobs — verify ownership before stopping anything

- `.local/server.pid` initially1021624, server log .local/server.log. Running
  system Python has old modules; restart using .venv after checking pid/cwd.
- `.local/import.pid` initially1023611: `tools/import_maps.py --all-arenas --force`.
  It is progressing through27 arena features; log .local/all-arenas.log and
  per-map .local/MAP_*.log. Do not overwrite reader DLL during reader execution.
- Old Fracture flat triangle expansion exceeded15GB; ONLY that owned compiler
  was terminated. New instance compiler successfully completed Fracture in212s:
  457 active walls/2052 edges,18,816 collisioninstances,1,005,314 unique triangles.
  import-report still records the cancelled attempt; reconcile after final pass.
- First imported maps have stale models. Recompile every scene after final
  geometry fixes; source assets need re-export only for new terrain support.

## Immediate next work / accuracy gap

1. Landscape terrain is NOT YET exported. Fracture has262 LandscapeComponents,
   262 LandscapeHeightfieldCollisionComponents,132 FastGeoContainers. Need
   decode heightmap plus visibility holes or cooked collision heightfield.
   Until supported, withhold route claims on maps with missing terrain.
   CUE Landscape collision reader currently discards cookedcollision bytes.
   ULandscapeComponent exposes GetHeightmap(), HeightmapScaleBias,
   ComponentSizeQuads/SubsectionSizeQuads/NumSubsections and weightmap allocations.
   Need raw UTexture2D mips PF_B8G8R8A8 (no screenshot reconstruction).
2. ProceduralMeshComponents present in Fracture are capture point visuals with
   no serialized vertex sections in sampled export. Inspect and classify;
   retain diagnostics rather than silently omitting possible collision.
3. Current compiler modelVersion4; update version when geometry changes.
   Add --recompile mode to importer, run all stale maps, refresh batch report.
4. Enforce Oodle hash already recorded in versions.json in setup.py, validate
   setup path. Review source coverage/diagnostic gates for every map.
5. Restart local server, finish browser QA (endpoints spacing, proxy maps,
   imports, filters/blocked walls, exports/saved routes, narrow viewport), save
   app verification screenshot, run appropriate tests, commit final work.
6. Update README/ARCHITECTURE for final collision/terrain coverage and limits.

## Browser session

cua_repl binding `tab` is iab tab2 URL above. On context continuation call
`await cua.rewriteDocumentation()` before using it. Reload after code edits.
Sites skill already read for local preview only; no publication.

## Milestone 5 — terrain and separate variants

TerrainExporter now successfully decodes262 Fracture patches from raw BGRA asset
heightmaps at the serialized collision mip, including visibility masks. Heights
are independently checked against CachedLocalBox. Hole boundaries are an
approximation (cells touching invisible samples are removed). Missing terrain,
mesh buffers, failed components and critical diagnostics withhold route edges.
Generated cells now belong only to the selected active root; Inferno V2 and the
older world no longer overlap. `--root` can select a different extracted world.
ModelVersion5 is rebuilding across all27 selected arena features using
`tools/import_maps.py --all-arenas --refresh`. Current batch PID1030707, log
.local/all-arenas-refresh.log. The original paused batch was terminated cleanly.
A standalone Fracture refresh completed:457walls/2086edges in225s. Batch may
repeat that map once because it reached it before the standalone publish.
Erosion exposed a zero-scale matrix; InstanceBVH now preserves flattened world
triangles instead of failing or dropping possible collision. Owned retry running
with log .local/Erosion-final.log (retained exec session33492).
Server now .venv Python PID1030989; restart after backend changes. It briefly
failed during restart because the previous process had not released its socket;
second start is serving correctly. Browser fresh iab tab3 binding atlasTab works;
old tab2 is an unreachable error page and can be closed. Academy routeP01→P06
now foursteps/4.5estimatedseconds/peak78. Saved route exists from QA.
32 tests pass. Reader now directly pins Microsoft.Bcl.Memory9.0.14, the patched
version (https://github.com/advisories/GHSA-73j8-2gch-69rq); upstream CUE's project
restore still warns about its own9.0.0 reference, while our reader's deps resolve
9.0.14. Final setup/build, UI export/filter/import/responsive QA, data coverage
report, documentation and commits remain. Source/graph exports and aim yaw/pitch
were added to UI and need a reload for QA.

## Milestone 6 — browser exports and QA

- ./setup.sh completed end-to-end against the prepared installation, including
  checksum validation, reader build, 1,794-package index and movement defaults.
- 35 tests pass; JS syntax check passes. Added attachment export/revision/Host
  checks and zero-scale plane test. Added tools/audit_maps.py to audit all27
  expected scenes, variant isolation, coverage, graph costs and buffer lengths.
- Browser tab3/atlasTab: real Academy route, easiest vs fastest, walk/portal
  filters, blocked-wall rerouting, max difficulty, saved-route cross-map restore,
  source dialog, route and full graph JSON downloads passed. Downloaded files:
  ~/Downloads/MAP_Academy-portal-route (1).json and MAP_Academy-wall-graph.json.
  Native attachment downloads replace client Blob exports for reliable browser
  download events. JSON was parsed and source/revision/edge counts verified.
- Fracture1327 shared buffers render without console errors. Labels now avoid
  overlap at distant zoom. Tested390x844 viewport: no horizontal overflow;
  planner stacks below canvas. Added accessible Arenas chooser for narrow screens.
  Temporary viewport override reset. Map selection now updates URL hash; stale
  mesh fetches cannot pollute a newly selected map's cache.
- Backend currently PID1033774, but restart once more to activate latest Host
  header guard. Own PID/cwd must be checked; wait for socket release before start.
- Batch PID1030707 currently compiles selected Inferno_V2,417walls, no mixed old
  variant. Glacier finished489walls/2209edges. Erosion retry finished447/1808,
 132terrainpatches, geometryUsable=true. Batch report still has original Erosion
  failure; reconcile after all imports by rerunning --all-arenas --refresh.
- Remaining: finish remaining imports, resolve any decoder coverage failures,
  test browser background import (creative empty map is a bounded useful test),
  restart final server, final audit/tests, save proof screenshot under .local/,
  write final validation report/docs, commit and remove owned stopped snapshot.

## Milestone 7 — final coverage corrections in progress

Final audit exposed two important gaps, now implemented:
- FeatureExporter follows cross-feature LevelStreamingAlwaysLoaded references.
  Virtual feature paths are resolved against the actual archive map-file index.
  Ozone Night now exports38packages/632meshes and compiles74walls/242edges (12s).
  MAP_Ozone and MAP_Ozone_Graffiti are shared sublevel libraries without their
  own root worlds. Excluded from --all-arenas (now25features) and hidden from
  arena list; still inspectable in import catalog as libraries.
- BrushExporter recovers actual BlockingVolume transforms/body setups and query
  responses. tools/finalize_scene.py filters portal rays by PortalLauncher and
  movement by Pawn channel; PhysicsOnly/disabled brushes do not block queries.
  Unread brushes or streaming dependencies withhold edges. InvisibleWall profiles
  stop Pawns while leaving PortalLauncher clear unless explicit responses differ.
  tools/refresh_coverage.py enriches old manifests and finalizes cached graphs.
  Compiler invokes finalization for future imports. finalizeVersion1 is required
  by audit. 39 tests pass including channel response checks.

The original arena batch PID1030707 finished all27 originally selected features.
Erosion original failure still in report, retry scene is valid. Brush metadata
batch PID1042009 completed/enriches existing maps; all sampled maps have no brush
errors (Grit43, Fracture22, Terra13 21). Coverage audit must be rerun after final
pass. An owned job is running tools/refresh_coverage.py then Terra13 recompile,
log .local/finalize-all.log then .local/Terra13-final.log (exec session tool result
supplies sessionID). Terra13 briefly had0edges because its previous import used
an old manifest before brush metadata arrived; regenerate it to restore candidates.
Ozone Night was separately rebuilt with dependencies and proper brush metadata.
Other old scenes are finalized cheaply without recomputing their geometric rays.

Remaining precise tasks:
1. Check finalize-all and Terra13 completion; inspect any geometryUsable=false
   on the25 actual arena features, fix or clearly qualify unresolved inputs.
2. Make import --refresh also account for finalizeVersion if needed; rerun it
   after coverage finalized to reconcile report quickly (should skip all scenes).
3. Update audit/tests to verify missing streaming and brush counts; final audit
   should pass25expectedfeatures. Current tests39 and JS syntax pass.
4. Restart owned server PID1033774 for latest Host/library metadata code. Own
   PID/cwd check, SIGTERM and wait socket release before daemon restart.
5. Browser background import test using Creative EmptySpace (small, zero-node
   case); verify job completion/error handling. All other UI QA already passed.
6. Reload stable Academy route, save app screenshot under ignored .local/ using
   cua bytes, embed it in final reply. Current atlasTab3 and atlasBrowser2;
   viewport override reset. Do not emit giant AX trees for500wall maps; read
   relevant DOM selectors. New caller must rewriteDocumentation after compaction.
7. Update README/ARCHITECTURE for query-specific brush checks and dependency
   resolution, create final docs/VALIDATION.md from audit counts, commit changes,
   clean owned stopped portal-atlas-assets container. Keep local server running.
