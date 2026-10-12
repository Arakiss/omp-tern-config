# Computer use: configured, available, verified

There are two separate backends. A permission granted to one does not authorize the other.

## omp native desktop prelude

The preset sets `computer.enabled=true`. The persistent JavaScript/Python eval API exposes window screenshots, Accessibility (AX), input and native menus through `computer`.

On macOS, the responsible application needs Screen Recording and Accessibility. In this Tern workflow, both were initially denied and the authorization requests reached Touch ID/password gates. After those gates were resolved, a fresh omp session independently reported `capture:true`, `input:true`, `ax:true`, with all three permission flags `granted`. A second fresh session resolved the exact Tern window and saved a real **1280 × 746** native screenshot, which was inspected. It requested no foreground control, changed no focus and closed its desktop session afterward. The private screenshot is not shipped. These observations apply to the tested MacBook, not to every installation; the installer itself grants no permissions.

Open **System Settings → Privacy & Security → Accessibility** and authorize Tern. Then review **Screen & System Audio Recording** for the responsible application. Relaunch the responsible app when macOS requests it; don't interrupt an active session just to restart it. Start a fresh omp desktop-control session after permission changes. `computer.close()` ends that control session and doesn't revoke OS permissions.

Never edit TCC databases, disable SIP, fabricate a permission result, or type the user's credentials. The installer does not grant permissions.

## CUA Driver

[Cua Driver](https://cua.ai/docs/cua-driver) is a separate signed local application with its own TCC identity, `com.trycua.driver`. Tested version: **0.33.4**.

```sh
python3 install.py --cua
```

This merges the optional server template into the active omp profile's `mcp.json`:

```json
{
  "mcpServers": {
    "cua-driver": {
      "type": "stdio",
      "command": "cua-driver",
      "args": ["mcp"],
      "enabled": true,
      "instructions": false,
      "timeout": 30000
    }
  }
}
```

The standalone MCP proxy uses CuaDriver's own daemon identity. Do not add `--direct` unless you intentionally want the invoking host to own the runtime and permissions. No network listener, account, token or cloud VM is required for this local integration. The existing daemon's security mode and upstream telemetry settings are not changed.

For an existing omp session, run `/mcp reload`; new sessions discover it at startup. MCP tools may appear as `xd://mcp__cua_driver_TOOL` devices in omp. Discover the advertised schemas instead of guessing them.

Optional official skill installation:

```sh
cua-driver skills install
```

## Verify before claiming readiness

```sh
cua-driver status
cua-driver doctor --json
cua-driver permissions status --json
cua-driver call list_windows '{}'
```

`permissions status` is read-only and does not run the Tahoe direct-capture consent probe. `screen_recording_capturable:null` and `direct_capture_status:not_checked` do not mean failure or success. Test a real exact-window capture using a current PID/window ID from `list_windows`:

```sh
cua-driver call get_window_state '{"pid":123,"window_id":456,"include_accessibility_tree":false,"screenshot_out_file":"/tmp/cua-window-proof.png","session":"setup-check"}'
```

The numeric IDs above illustrate the API; replace them with current IDs, never reuse someone else's. Inspect the image before claiming it captured the intended window. For interaction, take a fresh AX snapshot, use returned element tokens, act once, and verify from a fresh observation.

The setup was actually exercised with:

- CuaDriver Accessibility and Screen Recording both reported `true`, attributed to its own daemon.
- A real Tern window screenshot was saved and inspected, with AX controls and background-input routes available.
- An AX navigation action in System Settings was verified from the resulting Privacy & Security / Accessibility view.
- A fresh omp process invoked `get_window_state` through `xd://mcp__cua_driver_get_window_state`; the tool execution returned `isError:false` and produced a real **1568 × 914** image. The private image and process identifiers are not shipped in this repository.

## Native terminal attention

Use Tern's attention inbox, not cmux. The shared `skills/tern-terminal/SKILL.md` is installed by a full setup. The legacy cmux skill is ignored without removing other ignored skills.

For a real human gate, a Tern scenario can contain:

```text
alert waiting "macOS: authorize Accessibility for Tern with Touch ID in System Settings."
```

Send it with `tern ctl --file PATH` and verify the `waiting` entry in `tern ctl state` → `inbox.entries`. `Shift+Cmd+I` opens the native inbox in the tested keymap. Do not use this signal for routine progress or pretend a program is waiting when it isn't.

CUA's standard profile already allows ordinary observation and input without routine approvals. This setup does not enable unrestricted mode, attach to logged-in browser profiles, enable computer history or record a trajectory. Keep one controller, exact window targets, and explicit user authorization for consequential actions. Native permission/authentication prompts belong to the user.
