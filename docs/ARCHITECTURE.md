# Architecture

## Offline data pipeline

1. `prepare_assets.py` copies the installed archives and shipping executable from
   an isolated stopped Docker snapshot or an explicitly supplied installation.
   Inventory records archive sizes, IoStore versions, and TOC/executable hashes.
2. `extract_key.py` reads the known build's static encryption-key callback and
   delegate transformation. SHA256 and opcode guards reject other builds.
3. `reflection_emulator.py` maps PE bytes into Unicorn's private memory and
   emulates bounded static-initializer helpers, intercepting FName storage. It
   never uses the executable entrypoint, starts a game process, calls host OS
   functions from game code, injects into a process, or reads live game memory.
4. `native_metadata.py` and `build_mappings.py` recover native class/struct schemas
   and enum values from the initialized metadata. Unsupported schemas are rejected
   and reported. CUE4Parse reads Blueprint schemas from the cooked assets.
5. `AssetReader` mounts the encrypted archives with `GAME_Splitgate2`, resolves
   instances/templates/streaming levels, and exports original LOD vertex/index
   data. Resolved package-ID objects are retained because remastered meshes may
   have display paths that cannot be reopened. FastGeo instances are supported.
6. `extract_movement.py` records serialized base-character speed defaults,
   edition curve-table values, and navigation-agent dimensions with provenance.
7. `compile_scene.py` selects always-loaded levels and cooked generated cells,
   transforms geometry to world metres, identifies portal walls, builds a BVH,
   and checks directed angle and movement edges. Scene files publish atomically.

Private data lives under ignored `data/`. Git contains source, tests, dependency
versions, and handoff documentation. Browser assets are served locally.

## Wall graph

A physical wall is the user-facing node. Each directed edge records source and
arrival face, path/aim points, distance, incidence, angular clearance, camera turn,
estimated time, normalized difficulty, and qualification. Internally the search
state includes wall + face + forced-launch arrival, preventing impossible state
transitions across two independent graph edges.

Portal chains assume an active portal on the start wall. A placement edge replaces
the opposite portal and re-enters the current one. A walking/jumping edge includes
placing an entry portal on the arrival wall. Incoming portal traversal to a launch
wall is terminal while its forced outgoing motion remains unmodeled.

Direct movement checks use floor support and sampled height/lateral clearance.
The render mesh is a geometric proxy: neither an AI navmesh nor visual geometry
alone proves exact player collision. Critical geometry decoder failures produce
no routes rather than an unobstructed graph.

All edge costs are nonnegative. Dijkstra is used; straight-line distance is not an
admissible time heuristic in a graph with portal traversal. Difficulty is based on
geometry and assumed execution costs; no observed human success rates exist.

## Browser and local API

The Python server binds only `127.0.0.1`. It serves `web/`, compiled scene JSON,
and explicitly named mesh buffers. It does not expose arbitrary local files or
installation/key paths. Write requests reject foreign origins. Map import uses
allowlisted indexed feature IDs and structured subprocess arguments.

Three.js converts Unreal Z-up metres to browser Y-up coordinates. Instanced
meshes reuse geometry; wall overlays and route edges remain selectable. Browser
storage holds user route selections; JSON exports retain map revision, source,
model assumptions, selected nodes, and ordered edges.

## Validation

Unit tests verify segment intersections, nearest-hit acceleration, coordinate
transforms, route direction/face/launch state, objectives, and filters. HTTP tests
check static assets, API errors, local-origin writes, and file isolation. Optional
integration checks use the real installed data. Browser QA covers rendering,
route search, saving/export, filters, map changes/import, and responsive layout.
