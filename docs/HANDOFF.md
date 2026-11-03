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
