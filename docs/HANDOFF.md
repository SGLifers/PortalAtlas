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
