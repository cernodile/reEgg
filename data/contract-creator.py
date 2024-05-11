#!/bin/python
import json
import sys
sys.path.append("..")
import ei_pb2 as EIProto

boost_defs = {
"Supreme tachyon prism": "tachyon_prism_orange_big",
"Legendary tachyon prism (1000x 10m)": "tachyon_prism_orange",
"Legendary boost beacon (500x 10m)": "boost_beacon_orange",
"Legendary soul beacon (50x 10m)": "soul_beacon_orange",
"Epic tachyon prism (100x 2hr)": "tachyon_prism_purple_big",
"Epic soul beacon (50x 30)": "soul_beacon_purple",
"Powerful tachyon prism (100x 20m)": "tachyon_prism_purple",
"Jimbo's best bird feed (50x 2hr)": "jimbos_orange_big",
"Jimbo's best bird feed (50x 10m)": "jimbos_orange",
"Large boost beacon (5x 1hr)": "boost_beacon_blue_big"
}

obj = {"id": "", "name": "", "description": "", "duration": 0.0, "token_interval": 0.0, "egg": "", "goalsets": []}

def ask_for_string(preprint):
	while True:
		print(preprint, end="")
		x = input()
		if len(x) > 0:
			return x

def ask_for_float(preprint):
	while True:
		print(preprint, end="")
		x = input()
		try:
			val = float(x)
			return val
		except:
			continue

def parse_time(preprint):
	while True:
		print(preprint, end="")
		x = input()
		vals = x.split(" ")
		if len(vals) == 1:
			try:
				val = int(x)
				return val
			except:
				continue
		else:
			if len(vals) % 2 == 1:
				print("Write in following format: x d x h x m - or plain amount in minutes.")
			fail = False
			total = 0
			for i in range(0, len(vals), 2):
				try:
					intval = int(vals[i])
					suffix = vals[i + 1]
					if suffix.upper() == "D":
						intval *= 1440
					elif suffix.upper() == "H":
						intval *= 60
					total += intval
				except:
					fail = True
					break
			if fail:
				continue
			return total

def ask_for_quantity(preprint):
	while True:
		print(preprint, end="")
		x = input()
		vals = x.split(" ")
		if len(vals) == 2:
			try:
				val = int(vals[0])
				# why doesnt python have switch statements?
				multip = vals[1]
				if len(multip) != 1:
					print("Your quantifier must be 1 letter in length")
					continue
				if multip.upper() == "M":
					val *= 1000000
				elif multip.upper() == "B":
					val *= 1000000000
				elif multip.upper() == "T":
					val *= 1000000000000
				elif multip == "q":
					val *= 1000000000000000
				elif multip == "Q":
					val *= 1000000000000000000
				elif multip == 's':
					val *= 1000000000000000000000
				elif multip == 'S':
					val *= 1000000000000000000000000
				else:
					print("Couldn't identify your quantifier")
					continue
				return val
			except:
				continue
		else:
			print("Please enter the value in following format: VALUE QUANTIFIER (Example: 10 q)")

def parse_egg_type(preprint):
	while True:
		print(preprint, end="")
		x = input()
		if x == "?":
			print(", ".join(EIProto.Egg.keys()))
		else:
			try:
				egg_type = x.upper()
				EIProto.Egg.Value(egg_type)
				return egg_type
			except:
				continue

def parse_reward_type(preprint):
	while True:
		print(preprint, end="")
		x = input()
		if x == "?":
			print(", ".join(EIProto.RewardType.keys()))
		else:
			try:
				reward_type = x.upper()
				EIProto.RewardType.Value(reward_type)
				return reward_type
			except:
				continue

def parse_boost_type(preprint):
	while True:
		print(preprint, end="")
		x = input()
		if x == "?":
			for a, b in list(boost_defs.items()): print(a + ": " + b)
		else:
			try:
				boost_name = x.lower()
				if boost_name not in boost_defs.values():
					continue
				return boost_name
			except:
				continue


def create_goalset(type):
	print("Creating a " + type + " goalset")
	goal_amount = int(ask_for_float("How many goals: "))
	goals = []
	for i in range(0, goal_amount):
		print("Goal " + str(i + 1) + "/" + str(goal_amount))
		goal = {"deliver": 0, "reward_type": "", "reward_str": "", "reward_amt": 0}
		goal["deliver"] = ask_for_quantity("How many eggs to deliver? ")
		goal["reward_type"] = parse_reward_type("Enter reward type - type '?' for reference: ")
		if goal["reward_type"] == "BOOST":
			goal["reward_str"] = parse_boost_type("Type in boost type - type '?' for reference: ")
		elif goal["reward_type"] == "EPIC_RESEARCH_ITEM":
			goal["reward_str"] = ask_for_string("Type in epic research (check your backup for reference): ")
		goal["reward_amt"] = ask_for_float("How many rewarded? ")
		goals.append(goal)
	return goals

obj["id"] = ask_for_string("Enter contract ID: ")
obj["name"] = ask_for_string("Enter contract name: ")
obj["description"] = ask_for_string("Enter contract description: ")
obj["duration"] = parse_time("How many minutes does the contract last: ") * 60.0
obj["token_interval"] = ask_for_float("How many minutes to wait per reward token: ")
obj["egg"] = parse_egg_type("Enter egg type - type '?' if need reference: ")
obj["goalsets"].append(create_goalset("Elite"))
obj["goalsets"].append(create_goalset("Standard"))

print(json.dumps(obj, indent='\t'))
