local wmii = wmii

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

fg_normal = '#cccccc'
bg_normal = '#111111'
border_normal = '#333333'

fg_focus = '#cd8b00'
bg_focus = '#1c1f1c'
border_focus = '#cd8b00'

wmii.set_ctl({
        normcolors  = table.concat({fg_normal, bg_normal, border_normal}, ' '),
        focuscolors = table.concat({fg_focus, bg_focus, border_focus}, ' '),
        })

wmii.set_conf ({
        fg_normal = fg_normal,
        bg_normal = bg_normal,
        border_normal = border_normal,

        fg_focus = fg_focus,
        bg_focus = bg_focus,
        border_focus = border_focus,
        })


wmii.set_conf("messages.fg", border_normal)
wmii.set_conf("messages.bg", bg_focus)
wmii.set_conf("messages.border", bg_focus)

wmii.set_conf("volume.fg_low", "#777777")
wmii.set_conf("volume.fg_med", "#007700")
wmii.set_conf("volume.fg_high", "#cc0000")

wmii.set_conf("cpufreq.color_ondemand", table.concat({"#009900", bg_normal, border_normal}, ' '))
wmii.set_conf("cpufreq.color_performance", table.concat({"#990000", bg_normal, border_normal}, ' '))

wmii.set_conf("clock.fg_time", fg_focus)

wmii.set_conf("400_cpu.colors", table.concat({fg_normal, bg_normal, bg_normal}, ' '))

wmii.set_conf("301_mpd_status.colors", table.concat({bg_focus, bg_normal, bg_normal}, ' '))

wmii.set_conf("zzz999_client.colors", table.concat({fg_focus, bg_focus, bg_focus}, ' '))

wmii.set_conf("100_client_mode.colors", table.concat({fg_normal, bg_focus, bg_focus}, ' '))
wmii.set_conf("zzz888_client_mode.colors", table.concat({fg_normal, bg_focus, bg_focus}, ' '))

--wmii.set_conf("volume.border_color", bg_normal)

--wmii.set_conf("loadavg.bg", bg_normal)
--wmii.set_conf("loadavg.border", "#ffffff")

