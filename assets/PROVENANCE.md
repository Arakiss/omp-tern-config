# Wallpaper provenance

All nine WebP images in `wallpapers/` are original AI-generated assets, not movie/series frames, game screenshots or downloaded promotional images. No input film stills, logos or recognizable actors were supplied.

Generated on 2026-10-12 through omp's `generate_image` tool using the OpenAI Codex image transport. The provider reported `gpt-image-2-codex`.

| File | Returned dimensions | Returned quality | Art direction |
| --- | --- | --- | --- |
| `wallpapers/replicant.webp` | 1916 × 821 | medium | Blade Runner 2049-inspired monumental architecture, amber dust and cyan rain |
| `wallpapers/dunes.webp` | 1672 × 941 | low | Dune-inspired desert citadel, black basalt, bronze haze and eclipsed light |
| `wallpapers/grid.webp` | 1672 × 941 | low | Tron-inspired geometric landscape, restrained cyan grid and amber portal |
| `wallpapers/tron-ares.webp` | 1672 × 941 | medium | TRON: Ares-inspired black geometry, red light trails and cinematic rain |
| `wallpapers/altered-carbon.webp` | 1672 × 941 | medium | Altered Carbon-inspired vertical cyber-noir city and a koi hologram |
| `wallpapers/cyberpunk.webp` | 1672 × 941 | low | Retro-anime magenta/cyan noodle kiosk, CRT screens and red motorbike at the right edge |
| `wallpapers/ghost-shell.webp` | 1672 × 941 | low | Ghost in the Shell (1995)-inspired original cyborg investigator and jade harbor, hand-drawn anime look |
| `wallpapers/deus-ex.webp` | 1672 × 941 | low | Deus Ex-inspired black-and-gold architecture, faceted forms and geometric light |
| `wallpapers/retro-future.webp` | 1672 × 941 | low | Nostalgic pixel-art CRT workstation, cassette tapes, neon skyline and amber moon |

Cyberpunk, Ghost in the Shell and Retro Future were recomposed using their original generated scenes plus this repository's Replicant and Dunes images as composition references. The calm dark left/center is part of the artwork, not a global opacity filter; bright focal detail remains at the right. The dimensions and quality above are the final provider-returned results, not the requested size.

The repository's MIT permission grant applies to the assets to the extent contributors hold applicable rights. AI-generated images may not qualify for copyright protection in every jurisdiction. No affiliation with or endorsement by the respective film, series or game rights holders, omp, Tern or OpenAI is implied.

`assets/preview.png` is rendered by Tern's real headless renderer using the Replicant pack. Its text is a demonstration, not a benchmark or fabricated agent session. Private CUA screenshots, process identifiers and authentication dialogs are not included.

## English native coding demo

`assets/demo.gif`, `assets/demo.mp4` and `assets/demo-poster.png` derive from Tern's real headless renderer replaying a captured **omp 18.10.3** session on **Tern 0.8.3**. The isolated Orbit task added Unicode casefold search and JSON output; two real unittest cases and the CLI were executed successfully. `demo/project/` contains that resulting example and tests.

`demo/orbit.out.jsonl` is the vetted outbound native surface trace of the real run. Input/ack records were removed; it was checked for home-directory paths, email addresses and credential markers. Private desktop screenshots, authorization dialogs, other conversations and auth/config backups are excluded. The replay's wallpaper transitions and end holds are staged; model metrics in its surfaces are recorded observations from one small run, not a benchmark.

The native recording was rendered at 1440 × 900; the published GIF and MP4 are 1280 × 800, about 24.27 seconds. FFmpeg 8.1 encoded the H.264/yuv420p/faststart video and nominal-15-fps looping GIF; Gifsicle 1.97 optimized the GIF with mild `lossy=20`, preserving dimensions and timing. The poster is an actual frame from the edit step. `demo/record.py` and `demo/encode.py` reproduce the render/encoding without a new model request or desktop capture.

