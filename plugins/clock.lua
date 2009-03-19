--
-- Copyright (c) 2007, Bart Trojanowski <bart@jukie.net>
--
-- Simple clock applet for wmii bar.
--
local io = io
local os = os
local table = table
local string = string
local wmii = require("wmii")
local os = require("os")

module("clock")         -- module name
api_version=0.1         -- api version, see doc/plugin-api

-- ------------------------------------------------------------
-- CLOCK CONFIGURATION VARIABLES
--
-- these can be overridden by wmiirc

wmii.set_conf ("clock.update", wmii.get_conf("clock.update") or 1)
wmii.set_conf ("clock.date", wmii.get_conf("clock.date") or "%Y/%m/%d")
wmii.set_conf ("clock.time", wmii.get_conf("clock.time") or "%H:%M:%S")

-- ------------------------------------------------------------
-- MODULE VARIABLES

local time_widget = nil       -- the display on the bar
local date_widget = nil       -- the display on the bar
local timer = nil       -- the 1/second tick timer

-- ------------------------------------------------------------
-- THE TIMER WIDGET
--
-- Note that widgets are sorted in ascending order from left to
-- right on wmii's bar.  By convention this is a 3 digit number
-- and is prefixed to the widget name. There is currently no 
-- way to reorder a widget, but it is planed for a future release.
--
local date_widget = wmii.widget:new ("950_date")
local time_widget = wmii.widget:new ("955_time")

local function button_handler (ev, button)
    -- 3 is right button
    if button == 1 or button == 3 then
        local normcolors = wmii.get_ctl("normcolors")
        local fg_normal, bg_normal, border_normal = normcolors:match("(#%x+)%s+(#%x+)%s(#%x+)")
        fg_normal = wmii.get_conf("clock.fg_normal") or fg_normal
        bg_normal = wmii.get_conf("clock.bg_normal") or bg_normal

        local fg_month = wmii.get_conf("clock.fg_month") or fg_normal
        local bg_month = wmii.get_conf("clock.bg_month") or bg_normal

        local fg_today = wmii.get_conf("clock.fg_today") or bg_normal
        local bg_today = wmii.get_conf("clock.bg_today") or fg_normal

        local tmp = os.tmpname()
        local out = io.open(tmp, 'w')
        out:write("\n")

        local today = os.date("%e")
        local re = "([%^ ])"..today.."([$ ])"
        local rep = table.concat({
            "%1", 
            "^bg("..bg_today..")",
            "^fg("..fg_today..")",
            today,
            "^bg()^fg()%2",
        })

        local max = 0
        local lc = 0

        cal = io.popen('cal')
        for line in cal:lines() do
            local len = #line
            if len > max then
                max = len
            end
            line = line:gsub(re, rep)
            if lc == 0 then
                local prefix = {}
                if fg_month then
                    table.insert(prefix, "^fg("..fg_month..")")
                end
                if bg_month then
                    table.insert(prefix, "^bg("..bg_month..")")
                end
                line = table.concat(prefix)..line.."^fg()^bg()"
            end
            out:write(line .. string.rep(' ', max-len) .. '\n')
            lc = lc + 1
        end
        out:close()

        local exec = {"dzen2"}
        table.insert(exec, "-l")
        table.insert(exec, lc)
        table.insert(exec, "-fg '"..fg_normal.."'")
        table.insert(exec, "-bg '"..bg_normal.."'")
        table.insert(exec, "-p 5")
        table.insert(exec, "-ta c -x 1475 -y 15 -w 200 -sa c -e 'onstart=uncollapse;button1=exit'")
        table.insert(exec, "<")
        table.insert(exec, tmp)
        table.insert(exec, '&')
        wmii.log(table.concat(exec, ' '))

        dzen = os.execute(table.concat(exec, ' '))
    end
end

date_widget:add_event_handler("RightBarClick", button_handler)
time_widget:add_event_handler("RightBarClick", button_handler)



-- ------------------------------------------------------------
-- THE TIMER FUNCTION
--
-- The timer function will be called every X seconds.  If the 
-- timer function returns a number 

local function clock_timer (time_since_update)
        local normcolors = wmii.get_ctl("normcolors")
        local fg_normal, bg_normal, border_normal = normcolors:match("(#%x+)%s+(#%x+)%s(#%x+)")

        local fmt = wmii.get_conf("clock.date") or "%c"
        local fg = wmii.get_conf("clock.fg_date") or fg_normal
        local bg = wmii.get_conf("clock.bg_date") or bg_normal
        local border = wmii.get_conf("clock.border_date") or border_normal
        local color = nil
        if fg and bg and border then
            color = table.concat({fg, bg, border}, ' ')
        end
        date_widget:show (os.date(fmt), color)

        fmt = wmii.get_conf("clock.time") or "%c"
        fg = wmii.get_conf("clock.fg_time") or fg_normal
        bg = wmii.get_conf("clock.bg_time") or bg_normal
        border = wmii.get_conf("clock.border_time") or border_normal
        color = nil
        if fg and bg and border then
            color = table.concat({fg, bg, border}, ' ')
        end
        time_widget:show (os.date(fmt), color)

        -- returning a positive number of seconds before next wakeup, or
        -- nil (or no return at all) repeats the last schedule, or
        -- -1 to stop the timer
        return 1
end

local timer = wmii.timer:new (clock_timer, 1)

