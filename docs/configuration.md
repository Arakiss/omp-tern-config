# Adopting the pack without replacing a working setup

This repository distributes selected portable presets. Keep workstation-specific provider choices, local integrations and private paths in the active local configuration.

## Keep these boundaries

| Area | Source of truth | Adoption rule |
| --- | --- | --- |
| omp models, tools and approval policy | The active omp profile | Compare shipped keys before applying the full installer; do not replace a profile with a downloaded config file. |
| Tern fonts, layout and native chat | Tern's active settings | Keep working preferences unless a specific preset change is wanted. |
| Shared artwork and wallpaper plugin | This repository | Use the visual-only command to change the background without merging functional presets. |
| Accounts, sessions, MCP secrets and backups | Private local storage | Never copy them into this repository. |

A full install deliberately applies every shipped preset key. It replaces overlapping roles such as `default`, `plan` and `slow`, while retaining unrelated keys and additional roles. Approval policy remains unchanged unless `--autonomous` is supplied. A dry run reports destinations only.

## Visual-only adoption

From a clone, no full installation is required:

```sh
python3 tern_bg.py set cyberpunk-edgerunners-night
python3 tern_bg.py current
```

This installs or updates only the project's wallpaper plugin and its selection state. It leaves omp settings, Tern preferences, skills and other plugins untouched. Tern reloads plugins in open windows; sessions do not need to be closed. Rotation remains opt-in.

Check `tern plugin list` before adoption. If another plugin also paints the terminal background, keep its unrelated behavior and remove or disable only its competing background stylesheet after making a private backup. Two active background providers can hide each other's artwork depending on stylesheet precedence. The wallpaper command does not silently disable unrelated plugins.

Desktop images are separate downloads in the [gallery](../wallpapers/collections/README.md). Applying a terminal pack does not change desktop wallpaper or start a multi-monitor rotation schedule.

## Full preset adoption

```sh
python3 install.py --dry-run
python3 install.py --wallpaper cyberpunk-edgerunners-night
```

Use the full installer only when its model roles and visual preferences are the intended configuration. Authenticate providers separately. Keep the timestamped backups it prints outside Git, and retain the clone at its installed path if using the installed CLI symlinks.
