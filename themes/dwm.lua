local wmii = wmii

local hostnameio = io.popen("hostname")
local hostname = hostnameio:read()
hostnameio:close()
io.stderr:write("Found HOSTNAME: "..hostname.."\n")

--local fg_normal = '#e4eaf2'
--local bg_normal = '#07101f'
--local border_normal = '#07101f'

--local fg_focus = '#3e383c'
--local fg_focus = '#f09f29'
--local fg_focus = '#6a98c9'

--local fg_focus = '#f09f29'
--local bg_focus = '#0d1f38'
--local border_focus = '#07101f'

--local fg_normal = '#cccccc'
--local bg_normal = '#000000'
--local border_normal = '#7a7a7a'

--local fg_focus = '#98aeff'
--local bg_focus = '#1c1c1c'
--local border_focus = '#cd8b00'

--local fg_focus = '#ffffaa'
--local bg_focus = '#007700'
--local border_focus = '#88ff88'

--static const char selbordercolor[]  = "#0066ff";
--static const char selbgcolor[]      = "#0066ff";
--static const char selfgcolor[]      = "#ffffff";
--
--local fg_focus = '#cd8b00'
--local bg_focus = '#1c1f1c'
--local border_focus = '#cd8b00'
--local border_focus = bg_focus
--
--local fg_normal = '#cccccc'
--local bg_normal = '#111111'
--local border_normal = '#333333'

--static const char normbordercolor[] = "#cccccc";
--static const char normbgcolor[]     = "#cccccc";
--static const char normfgcolor[]     = "#000000";

local fg_normal = fg_normal

fg_focus = '#ffffff'
bg_focus = '#0066ff'
border_focus = '#0066ff'

fg_normal = '#000000'
bg_normal = '#cccccc'
border_normal = '#cccccc'

wmii.set_ctl({
        normcolors  = table.concat({fg_normal, bg_normal, border_normal}, ' '),
        focuscolors = table.concat({fg_focus, bg_focus, border_focus}, ' '),
        })

wmii.set_conf ({
        fg_normal = fg_normal,
        fg_focus = fg_focus,
        bg_normal = bg_normal,
        bg_focus = bg_focus,
        border_normal = border_normal,
        border_focus = border_focus,
        })


wmii.set_conf("messages.fg", bg_normal)
wmii.set_conf("messages.bg", bg_focus)
wmii.set_conf("messages.border", border_focus)

wmii.set_conf("volume.fg_low", "#777777")
wmii.set_conf("volume.fg_med", "#007700")
wmii.set_conf("volume.fg_high", "#cc0000")

if hostname then

    if hostname:find("murdock") then
        wmii.set_conf("cpufreq.color_ondemand", table.concat({"#009900", bg_normal, border_normal}, ' '))
        wmii.set_conf("cpufreq.color_performance", table.concat({"#990000", bg_normal, border_normal}, ' '))

        wmii.set_conf("clock.fg_time", bg_focus)

        wmii.load_plugin ("battery")
        wmii.set_conf("battery.names", "BAT0")

        wmii.set_conf("volume.mixer", "LineOut")
    end

    if hostname:find("baracus") then
        wmii.set_conf("400_cpu.colors", table.concat({fg_normal, bg_normal, bg_normal}, ' '))

        wmii.set_conf("301_mpd_status.colors", table.concat({"#9ec452", bg_normal, bg_normal}, ' '))
    end

    if hostname:find("baracus") or hostname:find("uiowa") then
        wmii.set_conf("100_client_mode.colors", table.concat({fg_normal, bg_normal, bg_normal}, ' '))
        wmii.set_conf("zzz105_client_mode.colors", table.concat({fg_normal, bg_normal, bg_normal}, ' '))

        wmii.set_conf({ 
            ["clock.border_date"] = bg_normal,
            ["clock.border_time"] = bg_normal,
        })

        wmii.set_conf("messages.border_color", bg_normal)
        wmii.set_conf("volume.border_color", bg_normal)

        wmii.set_conf("loadavg.bg", bg_normal)

        -- i like my current window to be displayed in the taskbar
        local client_name = wmii.widget:new("zzz100_client", nil, "lbar")

        local wmii_client_focused = wmii.client_focused
        local function client_focused(xid)
            local name = wmii.read("/client/"..xid.."/label")
            client_name:show(name, table.concat({fg_normal, bg_normal, bg_normal},' '))
            return wmii_client_focused(xid)
        end
        wmii.client_focused = client_focused

    end

end

