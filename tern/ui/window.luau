-- Static chrome only: no timers, processes, model changes or preference writes.
local stylesheet = tern.fs.read("hud.css", 32 * 1024)
local function apply()
  tern.css("hud", tern.fs.exists("enabled") and stylesheet or "")
end

tern.command({
  id = "on",
  title = "Enable retro-future HUD",
  group = "omp + Tern Config",
  run = function(_cx)
    tern.fs.write("enabled", "on\n")
    apply()
  end,
})
tern.command({
  id = "off",
  title = "Disable retro-future HUD",
  group = "omp + Tern Config",
  run = function(_cx)
    if tern.fs.exists("enabled") then
      tern.fs.remove("enabled")
    end
    apply()
  end,
})
tern.on("focus", function(_ev, _cx)
  apply()
end)
apply()
