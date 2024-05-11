# events.py - Event Scheduler for the server
import ei_pb2 as EIProto
import random
import datetime
import time

###
# BEHAVIOR ANALYSIS:
# Every Sunday - Soul Eggs 2x/3x event
# They typically last 24 hours
# Multiple *can* occur at once, albeit rarely
# Some events are more common than others.
# Thank you https://wasmegg-carpet.netlify.app/events/ for providing a database of past events.
###
# Changes compared to original game:
# No piggy bank events - you can't crack one open anyway.
###
# We can however, just lazily apply a "pre-set" map of events.
# If it's multiple events, it's an array, else it's an EIProto.EggIncEvent
###

event_calendar = []
def create_event_proto(type, internal_name, subtitle, multiplier):
	evt = EIProto.EggIncEvent()
	evt.type = type
	evt.multiplier = multiplier
	evt.subtitle = subtitle
	evt.identifier = internal_name
	return evt

event_calendar.append([
	create_event_proto("vehicle-sale", "VEHICLE SALE", "75% off all vehicles", 0.25),
	create_event_proto("drone-boost", "GENEROUS DRONES", "5x drone rewards", 5.0)
])
event_calendar.append(create_event_proto("epic-research-sale", "EPIC RESEARCH SALE", "30% off Epic Research Upgrades", 0.7))
event_calendar.append(create_event_proto("research-sale", "RESEARCH SALE", "70% off Research Upgrades", 0.3))
event_calendar.append(create_event_proto("hab-sale", "HAB SALE", "70% OFF HEN HOUSES!", 0.3))
event_calendar.append(create_event_proto("boost-sale", "BOOST SALE", "30% OFF BOOSTS!", 0.7))
event_calendar.append(create_event_proto("earnings-boost", "CASH BOOST", "3x EARNINGS!", 3.0))
event_calendar.append(create_event_proto("gift-boost", "GENEROUS GIFTS", "4x GIFTS!", 4.0))
event_calendar.append(create_event_proto("boost-duration", "BOOST TIME+", "DOUBLE BOOST TIME", 2.0))
event_calendar.append(create_event_proto("hab-sale", "HAB SALE", "70% OFF HEN HOUSES!", 0.3))
event_calendar.append(create_event_proto("vehicle-sale", "VEHICLE SALE", "75% off all vehicles", 0.25))
event_calendar.append(create_event_proto("drone-boost", "GENEROUS DRONES", "5x drone rewards", 5.0))
event_calendar.append(create_event_proto("research-sale", "RESEARCH SALE", "70% off Research Upgrades", 0.3))
event_calendar.append(create_event_proto("boost-sale", "BOOST SALE", "30% OFF BOOSTS!", 0.7))
event_calendar.append(create_event_proto("earnings-boost", "CASH BOOST", "3x EARNINGS!", 3.0))
event_calendar.append(create_event_proto("hab-sale", "HAB SALE", "70% OFF HEN HOUSES!", 0.3))
event_calendar.append(create_event_proto("boost-duration", "BOOST TIME+", "DOUBLE BOOST TIME", 2.0))
event_calendar.append(create_event_proto("gift-boost", "GENEROUS GIFTS", "4x GIFTS!", 4.0))
event_calendar.append(create_event_proto("epic-research-sale", "EPIC RESEARCH SALE", "30% off Epic Research Upgrades", 0.7))
event_calendar.append(create_event_proto("vehicle-sale", "VEHICLE SALE", "75% off all vehicles", 0.25))
event_calendar.append(create_event_proto("drone-boost", "GENEROUS DRONES", "5x drone rewards", 5.0))
event_calendar.append(create_event_proto("boost-duration", "BOOST TIME+", "DOUBLE BOOST TIME", 2.0))
event_calendar.append(create_event_proto("research-sale", "RESEARCH SALE", "70% off Research Upgrades", 0.3))
event_calendar.append(create_event_proto("earnings-boost", "CASH BOOST", "3x EARNINGS!", 3.0))
event_calendar.append(create_event_proto("hab-sale", "HAB SALE", "70% OFF HEN HOUSES!", 0.3))
event_calendar.append(create_event_proto("gift-boost", "GENEROUS GIFTS", "4x GIFTS!", 4.0))
event_calendar.append(create_event_proto("vehicle-sale", "VEHICLE SALE", "75% off all vehicles", 0.25))
event_calendar.append(create_event_proto("drone-boost", "GENEROUS DRONES", "5x drone rewards", 5.0))
event_calendar.append(create_event_proto("earnings-boost", "CASH BOOST", "3x EARNINGS!", 3.0))
event_calendar.append(create_event_proto("epic-research-sale", "EPIC RESEARCH SALE", "30% off Epic Research Upgrades", 0.7))
event_calendar.append(create_event_proto("boost-duration", "BOOST TIME+", "DOUBLE BOOST TIME", 2.0))
event_calendar.append(create_event_proto("hab-sale", "HAB SALE", "70% OFF HEN HOUSES!", 0.3))

triple_prestige_event = create_event_proto("prestige-boost", "PRESTIGE BOOST", "TRIPLE PRESTIGE!", 3.0)
double_prestige_event = create_event_proto("prestige-boost", "PRESTIGE BOOST", "DOUBLE PRESTIGE!", 2.0)

def get_active_events():
	date = datetime.datetime.today()
	delta = (datetime.datetime.combine(date + datetime.timedelta(days=1), datetime.time.min) - date).seconds
	cur_day = date.day
	res = []
	# it's a sunday, we have a fixed prestige event
	if date.isoweekday() == 7:
		# create a seed based off year and week to determine if we should use triple or double prestige this week
		iso_calendar = date.isocalendar()
		seed = int(str(iso_calendar.year) + str(iso_calendar.week))
		srng = random.Random(seed)
		# 50/50 chance of it being either
		if srng.random() < 0.5:
			res.append(double_prestige_event)
		else:
			res.append(triple_prestige_event)
	if type(event_calendar[cur_day]) is list:
		res = event_calendar[cur_day]
	else:
		res.append(event_calendar[cur_day])
	# Apply duration deltas
	for event in res:
		event.seconds_remaining = delta
	return res
