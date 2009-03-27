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
local tonumber = tonumber
local type = type

module("loadavg")
api_version=0.1

local palette = { "#888888",
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

local widget = wmii.widget:new ("800_loadavg")

local function loadavg_timer (time_since_update)

	local file = io.open("/proc/loadavg", "r")
	local bartext = nil
	local colors  = nil
	if file then
		local txt = file:read("*all")
		file:close()
		if type(txt) == 'string' then
			local one,five,ten = txt:match("^([%d%.]+)%s+([%d%.]+)%s+([%d%.]+)%s+")
			if type(one) == 'string' then
				bartext = string.format("%.1f %.1f %.1f", one, five, ten)
			end

			-- Now, colorization
			local current_avg = tonumber(one)
			if type(current_avg) == "number" then
				local index  = math.min(math.floor(current_avg * (#palette-1)) + 1, #palette)
                local normcolors = wmii.get_ctl("normcolors")
                local bg, border = normcolors:match("#%x+%s+(#%x+)%s+(#%x+)")
                bg = wmii.get_conf("loadavg.bg") or bg
                border = wmii.get_conf("loadavg.border") or border

                colors = table.concat({palette[index], bg, border}, ' ')
			end
		end
	end

	widget:show(bartext, colors)
	-- Returns:
	-- 	positive number of seconds before next wakeup
	-- 	nil, or no return, to repeat the last schedule
	-- 	-1 to stop the timer
	return 5
end

local timer = wmii.timer:new( loadavg_timer, 1)

