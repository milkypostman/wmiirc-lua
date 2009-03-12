--
-- Copyright (c) 2008, Dave O'Neill <dmo@dmo.ca>
--
-- Simple load applet for wmii bar.
--
local wmii = require("wmii")
local io = require("io")
local math = require("math")
local string = require("string")
local table = require("table")
local ipairs = ipairs
local tonumber = tonumber
local type = type

module("cpu")
api_version=0.1

local palette = { 
    "#888888",
    "#999988",
    "#AAAA88",
    "#BBBB88",

    "#CCCC88",
    "#CCBB88",
    "#CCAA88",

    "#DD9988",
    "#EE8888",
    "#FF4444",
}

local widgets = {}

local cpu = {}

local function updatewidget(i, current_avg)
    local colors
    if type(current_avg) == "number" then
        local index  = math.min(math.floor((current_avg/100) * (#palette-1)) + 1, #palette)
        local bg = wmii.get_conf("loadavg.bg")
        if bg then
            colors = table.concat({palette[index], bg, bg}, ' ')
        else
            local normal = wmii.get_ctl("normcolors")
            colors = string.gsub(normal, "^%S+", palette[index], 1)
        end
    end
    widgets[i]:show(current_avg .."%", colors)
end

local function loadavg_timer (time_since_update)
    local file = io.open('/proc/stat')

    local info = {}
    for line in file:lines() do
        if line:match("^cpu%d") then
            local fields = {}
            sep = " *"
            line:gsub("([^"..sep.."]*)"..sep, function(c) table.insert(fields, c) end)
            table.insert(info, fields)
        end
    end
    file:close()

    while #cpu < #info do
        table.insert(cpu, {usage = 0, total = 0, active = 0})
        table.insert(widgets, wmii.widget:new ("400_cpu"..(#cpu+1)))
    end

    local text = ""
    for i,v in ipairs(info) do
        local total = v[2] + v[3] + v[4] + v[5]
        local active = v[2] + v[3] + v[4]

        local diff_total = total - cpu[i].total
        local diff_active = active - cpu[i].active

        cpu[i].usage = math.floor(diff_active / diff_total *100)

        cpu[i].total = total
        cpu[i].active = active

        updatewidget(i, cpu[i].usage)
    end

    -- Returns:
    -- 	positive number of seconds before next wakeup
    -- 	nil, or no return, to repeat the last schedule
    -- 	-1 to stop the timer
    return 5
end

local timer = wmii.timer:new( loadavg_timer, 1)

