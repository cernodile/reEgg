# contracts.py - Contract Definitions parser and provider
import ei_pb2 as EIProto
import base64
import json
import time
import math

# TODO: Co-op contracts, toggle this off when we have them
ALL_SOLO_CONTRACTS = True

# Keep a cache of all contracts
contract_epoch = 1714867200
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
		# Leggacy ones are active for a week, twice per week
		i += 1
		expiry_time = (604800 * math.ceil(i / 2)) + (345600 if not i % 2 else 0) - time_since_epoch
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
	contract.ParseFromString(base64.b64decode(obj["proto"]))
	scaler = 1.0
	if ALL_SOLO_CONTRACTS:
		contract.coop_allowed = False
		# Not all contracts are made equal. If we divide it at an absolute, it becomes too easy
		# Still need to pinpoint the ratio based on experience.
		scale_factor = contract.max_coop_size * 0.35
		if scale_factor > 1.0:
			scaler = 1.0 / scale_factor
	return contract

def load_contracts():
	with open("data/contracts.json", "r") as file:
		obj = json.loads(file.read())
		time_since_epoch = time.time() - contract_epoch
		i = 0
		for source in obj:
			global_contract_db["legacy"].append(__convert_contract_to_proto(source))
			i += 1
			global_contract_db["legacy"][-1].expiration_time = (604800 * i) - time_since_epoch
	print(f'Loaded in {len(global_contract_db["legacy"])} "Leggacy" contracts, {len(global_contract_db["normal"])} to-schedule contracts')
	return

# Add the permanent contract here as well
def create_perma_contract():
	obj = {
		"id": "first-contract",
		"proto": "Cg5maXJzdC1jb250cmFjdBADIAA5AAAAAAAgzEBKE1lvdXIgRmlyc3QgQ29udHJhY3RSVVdlIGhlYXJkIHlvdSBhcmUgb3BlbiB0byBjb250cmFjdCB3b3JrISBIZWxwIGZpbGwgdGhpcyBvcmRlciBmcm9tIHRoZSBsb2NhbCBwaGFybWFjeSF5AAAAAAAAFECCATAKFggBEQAAAAAAavhAGAIpAAAAAABAf0AKFggBEQAAACBfoPJBGAYpAAAAAACIw0CCATAKFggBEQAAAAAAavhAGAIpAAAAAAAAaEAKFggBEQAAACBfoPJBGAYpAAAAAACIw0A="
	}
	contract = __convert_contract_to_proto(obj)
	# The permanent "first contract" is a special case where it should never expire and it should also not appear after 5000 Soul Eggs
	contract.expiration_time = 100000000.0
	contract.max_soul_eggs = 5000.0
	return contract

global_contract_db["permanent"].append(create_perma_contract())
