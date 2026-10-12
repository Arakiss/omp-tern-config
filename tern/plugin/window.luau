-- Decode once at load. No timers, network access or external processes.
local image = tern.base64.encode(tern.fs.read("wallpaper.webp", 8 * 1024 * 1024))
tern.css("wallpaper", [[
.tn-stage .tn-pane .tn-body {
  background-color: #080f14;
  background-image: url("data:image/webp;base64,]] .. image .. [[");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
/* Protect the small progress strip, not the wallpaper or the whole pane. */
.tn-stage .sf-dock > .sf-row {
  background-color: #171c25;
  border-radius: 6px;
}
]])
