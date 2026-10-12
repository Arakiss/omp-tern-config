---
name: tern-terminal
description: Operate Tern's native terminal control API, panes and attention notifications. Use for Tern terminal workflows; never route Tern notifications through cmux.
---

# Tern terminal

Use the actual Tern terminal, not another terminal's commands. cmux is not a dependency or notification fallback.

## Inspect before controlling

- `tern --help`, `tern COMMAND --help`, and `tern help dev` describe the installed build.
- `tern ctl state` reports the active pane, tabs, theme and attention inbox.
- `tern ls`, `tern inspect`, and `tern capture` inspect sessions and output.
- `tern plugin types DIR` generates the installed build's Luau API declarations.
- Retain existing sessions and don't send shell commands into a busy agent pane.

## Human attention, native to Tern

Notify only for an actual human gate: login, 2FA, CAPTCHA, credential entry, legal signature or administrator authentication. Name the service/app, exact action, and window when known. Never include secrets.

Write a temporary scenario file with one command (quote the message):

```text
alert waiting "macOS: authorize Accessibility for Tern using Touch ID in System Settings."
```

Send it with `tern ctl --file PATH`. This records a native waiting/attention event for the focused pane. Verify `tern ctl state` shows the real entry in `inbox.entries`; use `tern ctl inbox` only when revealing the inbox is useful. This is a genuine request for attention, not a way to fabricate program output or completion.

For a transient in-terminal message, the installed Luau API exposes:

```sh
tern ctl carly lua 'cx:toast("info", "Action needed", "Exact action and app")'
```

A successful command alone does not prove visibility. Inspect Tern's actual surface with the available computer-use backend or native state. Do not send routine progress or normal command failures as attention events. Never fall back to cmux.

## Desktop use and permissions

Follow the host's required computer-use tool policy. If CUA is explicitly requested or the native prelude is unavailable, use `cua-driver` and its official skill. Keep one controller, exact window targets, fresh snapshots and post-action verification. A CUA daemon's macOS permissions are distinct from Tern's.

macOS authentication prompts belong to the user. Don't type credentials, auto-approve security dialogs, edit TCC databases or weaken system protections. A checkbox changing before authentication completes is not proof of a granted permission.

## Configuration

The `omp-tern-config` installer preserves unrelated settings and backs up overwritten owned files. Native Tern completion, editing and chat surfaces are already enabled in the tested defaults. The optional wallpaper plugin is local-only. Discover current capabilities rather than copying assumptions from cmux or another terminal.
