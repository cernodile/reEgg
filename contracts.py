# contracts.py - Contract Definitions parser and provider
import ei_pb2 as EIProto
import json
import time

# Keep a cache of all contracts
contract_epoch = int(time.time())
global_contract_db = {"legacy": [], "normal": [], "permanent": []}

def get_active_contracts():
	# TODO: Shift the epoch when a full run of leggacys is done.
	# TODO: Don't iterate all the contracts, calculate where appropriate on starting index
	# Return an array of Contract objects
	list = [global_contract_db["permanent"][0]]
	# Iterate leggacy
	time_since_epoch = time.time() - contract_epoch
	i = 0
	for contract in global_contract_db["legacy"]:
		# Leggacy ones are active for a week, one per week
		i += 1
		expiry_time = (604800 * i) - time_since_epoch
		# It's expired, get the next one
		if expiry_time < 0:
			continue
		# It's already next week's contract, don't process more
		if expiry_time > 604800:
			break
		contract.expiration_time = expiry_time
		list.append(contract)
	# Add regular contracts here when implemented
	# DESIGN QUESTION: Do we even *want* regular contracts? Could just run two "leggacy" branches in parallel.
	return list

def __convert_contract_to_proto(obj):
	# Map values from JSON object to Protobuf object.
	contract = EIProto.Contract()
	contract.identifier = obj["id"]
	contract.name = obj["name"]
	contract.description = obj["description"]
	contract.egg = EIProto.Egg.Value(obj["egg"])
	contract.minutes_per_token = obj["token_interval"]
	contract.length_seconds = obj["duration"]
	contract.coop_allowed = False
	for goal_set_src in obj["goalsets"]:
		goal_set = contract.goal_sets.add()
		for goal_src in goal_set_src:
			goal = goal_set.goals.add()
			goal.type = EIProto.GoalType.EGGS_LAID
			goal.target_amount = goal_src["deliver"]
			goal.reward_type = EIProto.RewardType.Value(goal_src["reward_type"])
			if goal.reward_type == EIProto.RewardType.BOOST:
				goal.reward_sub_type = goal_src["reward_str"]
			goal.reward_amount = goal_src["reward_amt"]
	return contract

def load_contracts():
	with open("data/contracts.json", "r") as file:
		obj = json.loads(file.read())
		global contract_epoch
		contract_epoch = obj["epoch"]
		time_since_epoch = time.time() - contract_epoch
		i = 0
		for source in obj["legacy"]:
			global_contract_db["legacy"].append(__convert_contract_to_proto(source))
			i += 1
			global_contract_db["legacy"][-1].expiration_time = (604800 * i) - time_since_epoch
	print(f'Loaded in {len(global_contract_db["legacy"])} "Leggacy" contracts, {len(global_contract_db["normal"])} to-schedule contracts')
	return

# Add the permanent contract here as well
def create_perma_contract():
	obj = {
		"id": "first-contract",
		"name": "Your First Contract",
		"description": "We heard you are open to contract work! Help fill this order from the local pharmacy!",
		"egg": "MEDICAL",
		"duration": 14400.0,
		"token_interval": 5.0,
		"goalsets": [
			[
				{"deliver": 100000.0, "reward_type": "GOLD", "reward_amt": 500},
				{"deliver": 5000000000.0, "reward_type": "PIGGY_FILL", "reward_amt": 10000}
			],
			[
				{"deliver": 100000.0, "reward_type": "GOLD", "reward_amt": 192},
				{"deliver": 5000000000.0, "reward_type": "PIGGY_FILL", "reward_amt": 10000}
			]
		]
	}
	contract = __convert_contract_to_proto(obj)
	# The permanent "first contract" is a special case where it should never expire and it should also not appear after 5000 Soul Eggs
	contract.expiration_time = 100000000.0
	contract.max_soul_eggs = 5000.0
	return contract

global_contract_db["permanent"].append(create_perma_contract())
