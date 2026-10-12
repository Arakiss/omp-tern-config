# Changelog

## 1.3.0 — 2026-10-12

- Added the standard-library `tern-bg` CLI with `list`, `current`, `set`, `next` and `prev` controls over the nine-pack catalogue.
- Added the original Retro Future pixel-art wallpaper, appended after Deus Ex without changing the earlier catalogue order.
- Added opt-in macOS wallpaper rotation via a project-owned user LaunchAgent, configurable with `rotate --every 15m` and managed with `status` and `stop`; rotation is off by default.
- Unified full installation and visual-only commands behind one shared wallpaper application path, with atomic replacements, serialized transitions and bounded wallpaper backups for periodic changes.
- Full installation now creates a safe `~/.local/bin/tern-bg` symlink; dry runs create nothing, and unrelated executables are never overwritten.
- Replaced the installer's visual-only mode with the dedicated CLI while retaining full preset merging, private backups, initial wallpaper selection and optional CUA integration.
- Added public GitHub clone/install instructions and documented PATH, repository availability, ordered wraparound and rotation controls.
- Reworked Cyberpunk and Ghost in the Shell with nostalgic hand-drawn anime direction and composition referenced to the original Replicant/Dunes packs; preserved bright artwork without a full-image dimming filter.
- Added the opt-in native retro-future HUD plugin and `tern-ui on|off|status`; disabling it restores existing chrome without modifying preferences, models or wallpaper.
- Kept input styling native and added a small opaque progress strip for readability without obscuring the entire background.
- Reworked the README around a short purpose, genuine preview, 60-second tour, command reference, visible wallpaper thumbnails and explicit limits, following patterns from Arakiss's public projects.
- Added a real English Orbit coding-session trace, native Tern replay/recording script, high-quality looping GIF, H.264 video and an actual edit-step poster; no private desktop capture or invented tool results are published.
- Added reproducible FFmpeg/Gifsicle media encoding and isolated Orbit example tests to CI; the demo is explicitly a staged replay, not a benchmark.
- Retained native theme backgrounds in HUD chrome to avoid dark forced fills on light themes; kept the live terminal's HUD and periodic rotation disabled.
- Verified that native omp capture, input and AX permissions are now granted, and inspected a real exact-window native capture in a fresh session; CUA remains separately configured.

## 1.2.0 — 2026-10-12

- Added five original wallpaper packs: TRON: Ares, Altered Carbon, Cyberpunk, Ghost in the Shell and Deus Ex.
- Expanded the shared installer catalogue to eight packs; retained the Replicant default and wallpaper-only configuration isolation.
- Documented each generated asset's actual returned dimensions and quality, with a primary-source link identifying TRON: Ares (2025).
- Installed and visually inspected every new pack in the real Tern window using CUA; verified that omp settings, MCP, Tern settings and the native Tern skill remained byte-identical.

## 1.1.0 — 2026-10-12

- Renamed the repository and public identity to `omp-tern-config`; Replicant is now only a visual pack.
- Added optional local CUA Driver integration over stdio MCP, preserving other servers and the existing daemon's security mode.
- Verified a real CUA capture through omp's MCP transport, plus AX observation and native UI navigation.
- Installed a Tern-native attention skill; ignored the obsolete cmux skill while preserving other ignored entries. Verified the waiting event in Tern's inbox.
- Added original Dunes and Grid image packs and isolated visual switching that leaves functional configuration untouched.
- Updated the public preview, image provenance and computer-use permission documentation.

## 1.0.0 — 2026-10-12

- Curated omp + Tern presets with readable Titanium styling and visible agent resource usage.
- Portable local wallpaper plugin and original generated cinematic WebP asset.
- Standard-library Python installer preserving unrelated settings and custom model roles, with private timestamped backups and explicit autonomy opt-in.
- Verified installation and native live reload on omp 18.10.2 / Tern 0.8.3 on macOS.
- Regression tests for nested preference preservation, custom model roles, failed atomic writes and private file permissions.
- MIT license, asset provenance, public preview and sharing copy.
