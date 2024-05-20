############
# Egg Inc v1.12.13 (Android Build 111121) server emulator
# Read the blog post at https://based.quest/reverse-engineering-a-mobile-app-protobuf-api/
############
import base64
import datetime
import math
import time
import zlib

import ei_pb2 as EIProto

from flask import Flask
from flask import request

import contracts
import events
import db_utils
import db_store

upgrade_cache = {}

app = Flask(__name__)
contracts.load_contracts()
db_store.create_backups_db()
db_store.create_contracts_db()

contracts_motd = "Welcome to reEgg Server Emulator\nLeggacy contracts available every Monday/Friday"

def calculate_backup_checksum(SaveBackup):
	# WIP - Need to figure out what the 0 and 61 still are.
	# 61 - best fit is SaveBackup.mission.missions array length, which same time makes zero sense
	# 0 - unknown still
	return int(SaveBackup.game.golden_eggs_earned) + 0 + SaveBackup.farms[0].num_chickens + 61 + int(math.log10(SaveBackup.game.lifetime_cash_earned) * 100)

# /ei/ routes
@app.route('/ei/first_contact', methods=['POST'])
def ei_first_contact():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	ContactReq = EIProto.EggIncFirstContactRequest()
	ContactReq.ParseFromString(data)
	ContactResp = EIProto.EggIncFirstContactResponse()
	Backups = db_store.get_backups(ContactReq.user_id)
	if len(Backups) > 0:
		# Lets process backups - check for any forced ones first
		now = datetime.datetime.now()
		cleanup_ids = []
		for backup in Backups:
			if backup[2] == True:
				# Force backup found - lets serialize the payload
				SaveBackup = EIProto.Backup()
				try:
					SaveBackup.ParseFromString(zlib.decompress(base64.b64decode(backup[3])))
					SaveBackup.force_backup = True
					SaveBackup.force_offer_backup = True
					ContactResp.backup.CopyFrom(SaveBackup)
					db_store.update_backup(backup[0], backup[3], False)
					break
				except:
					print("Failed to force serve backup - perhaps some logic error?")
					break
			else:
				then = datetime.datetime.fromtimestamp(backup[1])
			if (now - then).days > 1:
					cleanup_ids.append(backup[0])
		if len(cleanup_ids) > 0:
			db_store.cleanup_backups(cleanup_ids)
		# TODO: Check for soul eggs/eggs of prophecy and determine algorithm for "is it worth offering?"
	elif ContactReq.user_id in upgrade_cache:
		print("Found an unupgraded save - lets upgrade the permit level to Pro")
		ContactResp.backup.CopyFrom(cache[ContactReq.user_id])
		del upgrade_cache[ContactReq.user_id]
	return base64.b64encode(ContactResp.SerializeToString())

@app.route('/ei/save_backup', methods=['POST'])
def ei_save_backup():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	SaveBackup = EIProto.Backup()
	SaveBackup.ParseFromString(bytes(data))
	if SaveBackup.game.permit_level == 0:
		SaveBackup.game.permit_level = 1
		SaveBackup.force_backup = True
		SaveBackup.force_offer_backup = True
		upgrade_cache[SaveBackup.user_id] = SaveBackup
	else:
		# start storing backups after permit upgrades
		db_store.add_backup(SaveBackup.user_id, base64.b64encode(zlib.compress(SaveBackup.SerializeToString())))
	return ""

@app.route('/ei/user_data_info', methods=['POST'])
def ei_user_data_info():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	udiReq = EIProto.UserDataInfoRequest()
	udiReq.ParseFromString(data)
	udiRes = EIProto.UserDataInfoResponse()
	Backups = db_store.get_backups(udiReq.device_id)
	if len(Backups) == 0:
		return base64.b64encode(udiRes.SerializeToString())
	LastBackup = EIProto.Backup()
	LastBackup.ParseFromString(zlib.decompress(base64.b64decode(Backups[-1][3])))
	udiRes.backup_checksum = LastBackup.checksum
	udiRes.backup_total_cash = LastBackup.game.lifetime_cash_earned
	memberships = db_store.get_coop_memberships(udiReq.device_id)
	for membership in memberships:
		udiRes.coop_memberships.append(membership[1])
	return base64.b64encode(udiRes.SerializeToString())

@app.route('/ei/daily_gift_info', methods=['POST'])
def ei_daily_gift_info():
	DateInfo = (datetime.datetime.now() - datetime.datetime(1970, 1, 1))
	GiftResponse = EIProto.DailyGiftInfo()
	GiftResponse.current_day = DateInfo.days
	GiftResponse.seconds_to_next_day = 86400 - DateInfo.seconds
	return base64.b64encode(GiftResponse.SerializeToString())

def populate_contracts_response(obj):
	if obj is None:
		obj = EIProto.ContractsResponse()
	obj.warning_message = contracts_motd
	for contract in contracts.get_active_contracts():
		c = obj.contracts.add()
		c.CopyFrom(contract)
	return obj

@app.route('/ei/get_contracts', methods=['POST'])
def ei_get_contracts():
	return base64.b64encode(populate_contracts_response(None).SerializeToString())

@app.route('/ei/get_periodicals', methods=['POST'])
def ei_periodicals_request():
	PeriodicalResp = EIProto.PeriodicalsResponse()
	populate_contracts_response(PeriodicalResp.contracts)
	for evt in events.get_active_events():
		e = PeriodicalResp.events.events.add()
		e.CopyFrom(evt)
	return base64.b64encode(PeriodicalResp.SerializeToString())

@app.route('/ei/query_coop', methods=['POST'])
def ei_query_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	QueryCoop = EIProto.QueryCoopRequest()
	QueryCoop.ParseFromString(data)
	QueryCoopResp = EIProto.QueryCoopResponse()
	ContractInfo = contracts.get_contract_by_identifier(QueryCoop.contract_identifier)
	if ContractInfo is None:
		QueryCoopResp.exists = True
		return base64.b64encode(QueryCoopResp.SerializeToString())
	db_query = db_store.is_coop_identifier_used(QueryCoop.coop_identifier, QueryCoop.contract_identifier)
	if db_query is not None:
		QueryCoopResp.exists = True
	else:
		QueryCoopResp.exists = False
	if QueryCoopResp.exists:
		if QueryCoop.league != db_query:
			QueryCoopResp.different_league = True
		else:
			if db_store.is_coop_full(QueryCoop.coop_identifier, ContractInfo.max_coop_size):
				QueryCoopResp.full = True
	return base64.b64encode(QueryCoopResp.SerializeToString())

@app.route('/ei/create_coop', methods=['POST'])
def ei_create_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	CreateCoop = EIProto.CreateCoopRequest()
	CreateCoop.ParseFromString(data)
	CreateResponse = EIProto.CreateCoopResponse()
	# Double check if in use
	db_query = db_store.is_coop_identifier_used(CreateCoop.coop_identifier, CreateCoop.contract_identifier)
	if db_query is not None:
		CreateResponse.success = False
		CreateResponse.message = "That co-op already exists."
		return base64.b64encode(CreateResponse.SerializeToString())
	# Can we identify the contract?
	contract = contracts.get_contract_by_identifier(CreateCoop.contract_identifier)
	if contract is None:
		CreateResponse.success = False
		CreateResponse.message = "You're no fun."
		return base64.b64encode(CreateResponse.SerializeToString())
	# Calculate timestamp of the contract so we can later tell actual seconds left to new joins.
	stamp = int(time.time() - contract.length_seconds + CreateCoop.seconds_remaining)
	# Actually creating the co-op now.
	res = db_store.create_coop_contract(CreateCoop.coop_identifier, CreateCoop.contract_identifier, CreateCoop.league, stamp, CreateCoop.user_id, CreateCoop.user_name)
	if not res:
		CreateResponse.success = False
		CreateResponse.message = "Unknown error with your request."
	else:
		CreateResponse.success = True
		CreateResponse.message = "Co-op created."
	return base64.b64encode(CreateResponse.SerializeToString())

def construct_contract_status(coop_name, contract_name, requester_id):
	StatusResp = EIProto.ContractCoopStatusResponse()
	BaseInfo = db_store.get_contract_info(coop_name, contract_name)
	ContribInfo = db_store.get_coop_contributors(coop_name, contract_name)
	ContractInfo = contracts.get_contract_by_identifier(contract_name)
	if BaseInfo is None or ContribInfo is None or ContractInfo is None:
		return None
	i = 0
	for x in ContribInfo:
		i += 1
		contributor = StatusResp.contributors.add()
		contributor.user_id = x[0] if x[0] == requester_id else "cool-guy-" + str(i)
		contributor.user_name = x[3]
		contributor.contribution_amount = x[5]
		StatusResp.total_amount += x[5]
		contributor.contribution_rate = x[6]
		contributor.soul_power = x[7]
		contributor.active = not (int(time.time()) - x[4]) >= 86400
		contributor.boost_tokens = x[8]
	StatusResp.coop_identifier = coop_name
	StatusResp.contract_identifier = contract_name
	StatusResp.auto_generated = BaseInfo[7]
	StatusResp.public = BaseInfo[6]
	StatusResp.creator_id = "hidden-for-safety" if requester_id != BaseInfo[5] else BaseInfo[5]
	StatusResp.seconds_remaining = (BaseInfo[4] + int(ContractInfo.length_seconds)) - int(time.time())
	GiftInfo = db_store.get_coop_gifts(coop_name, contract_name, requester_id)
	for g in GiftInfo:
		Gift = StatusResp.gifts.add()
		Gift.user_id = "hidden-for-safety"
		Gift.user_name = g[3]
		Gift.amount = g[4]
	return StatusResp

@app.route('/ei/coop_status', methods=['POST'])
def ei_coop_status():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	StatusReq = EIProto.ContractCoopStatusRequest()
	StatusReq.ParseFromString(data)
	return base64.b64encode(construct_contract_status(StatusReq.coop_identifier, StatusReq.contract_identifier, StatusReq.user_id).SerializeToString())

@app.route('/ei/update_coop_status', methods=['POST'])
def ei_update_coop_status():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	UpdateReq = EIProto.ContractCoopStatusUpdateRequest()
	UpdateReq.ParseFromString(data)
	db_store.update_coop_contribution(UpdateReq.coop_identifier, UpdateReq.contract_identifier, UpdateReq.user_id, UpdateReq.amount, UpdateReq.rate, UpdateReq.soul_power, UpdateReq.boost_tokens, UpdateReq.time_cheats_detected)
	Resp = EIProto.ContractCoopStatusUpdateResponse()
	Resp.finalized = True
	return base64.b64encode(Resp.SerializeToString())

@app.route('/ei/join_coop', methods=['POST'])
def ei_join_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	JoinCoopRequest = EIProto.JoinCoopRequest()
	JoinCoopRequest.ParseFromString(data)
	JoinResponse = EIProto.JoinCoopResponse()
	JoinResponse.coop_identifier = JoinCoopRequest.coop_identifier
	ContractInfo = contracts.get_contract_by_identifier(JoinCoopRequest.contract_identifier)
	if ContractInfo is None:
		JoinResponse.success = False
		JoinResponse.banned = True
		JoinResponse.message = "You must be fun at parties."
		return base64.b64encode(JoinResponse.SerializeToString())
	db_query = db_store.is_coop_identifier_used(JoinCoopRequest.coop_identifier, JoinCoopRequest.contract_identifier)
	if db_query is None:
		JoinResponse.success = False
		JoinResponse.message = "That co-op doesn't exist."
		return base64.b64encode(JoinResponse.SerializeToString())
	if db_query != JoinCoopRequest.league:
		JoinResponse.success = False
		JoinResponse.message = "You can't join a " + ("Elite" if db_query == 1 else "Standard") + " contract."
		return base64.b64encode(JoinResponse.SerializeToString())
	BaseInfo = db_store.get_contract_info(JoinCoopRequest.coop_identifier, JoinCoopRequest.contract_identifier)
	ContribInfo = db_store.get_coop_contributors(JoinCoopRequest.coop_identifier, JoinCoopRequest.contract_identifier)
	if len(ContribInfo) - 1 >= ContractInfo.max_coop_size:
		JoinResponse.success = False
		JoinResponse.message = "Co-op is full!"
		return base64.b64encode(JoinResponse.SerializeToString())
	# TODO: bans from coops
	db_store.insert_coop_contribution(JoinCoopRequest.coop_identifier, JoinCoopRequest.user_id, JoinCoopRequest.user_name, JoinCoopRequest.soul_power)
	JoinResponse.success = True
	JoinResponse.banned = False
	JoinResponse.seconds_remaining = (BaseInfo[4] + int(ContractInfo.length_seconds)) - int(time.time())
	return base64.b64encode(JoinResponse.SerializeToString())

@app.route('/ei/auto_join_coop', methods=['POST'])
def ei_auto_join_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	AutoJoinCoopRequest = EIProto.AutoJoinCoopRequest()
	AutoJoinCoopRequest.ParseFromString(data)
	Resp = EIProto.JoinCoopResponse()
	Contract = contracts.get_contract_by_identifier(AutoJoinCoopRequest.contract_identifier)
	if Contract is None:
		Resp.success = False
		Resp.message = "Invalid contract."
		return base64.b64encode(Resp.SerializeToString())
	coops = db_store.get_public_coops(AutoJoinCoopRequest.contract_identifier)
	Resp.success = False
	for coop in coops:
		coop_identifier = coop[0]
		# TODO: Ban check
		if not db_store.is_coop_full(coop_identifier, Contract.max_coop_size):
			Resp.success = True
			db_store.insert_coop_contribution(coop_identifier, AutoJoinCoopRequest.contract_identifier, AutoJoinCoopRequest.user_id, AutoJoinCoopRequest.user_name, AutoJoinCoopRequest.soul_power)
			BaseInfo = db_store.get_contract_info(coop_identifier)
			Resp.coop_identifier = coop_identifier
			Resp.banned = False
			Resp.seconds_remaining = (BaseInfo[4] + int(Contract.length_seconds)) - int(time.time())
			break
	if Resp.success == False:
		Resp.message = "No public contracts found."
	# TODO: Auto-create co-op if none found
	return base64.b64encode(Resp.SerializeToString())

@app.route('/ei/gift_player_coop', methods=['POST'])
def ei_gift_player():
	# TODO: How do we validate the player even has as many boost tokens as they are about to gift?
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	GiftReq = EIProto.GiftPlayerCoopRequest()
	GiftReq.ParseFromString(data)
	if not db_store.is_user_in_coop(GiftReq.requesting_user_id, GiftReq.coop_identifier, GiftReq.contract_identifier):
		return "", 404
	BaseInfo = db_store.get_contract_info(GiftReq.coop_identifier, GiftReq.contract_identifier)
	ContribInfo = db_store.get_coop_contributors(GiftReq.coop_identifier, GiftReq.contract_identifier)
	if len(ContribInfo) <= 1:
		return "", 404
	if GiftReq.player_identifier.startswith("cool-guy-"):
		tmp = GiftReq.player_identifier[9:]
		try:
			id = int(tmp) - 1
			if id >= len(ContribInfo) or id < 0:
				return "", 404
			real_id = ContribInfo[id][0]
			db_store.add_coop_gift(GiftReq.coop_identifier, GiftReq.contract_identifier, GiftReq.amount, GiftReq.requesting_user_name, real_id)
			return base64.b64encode(construct_contract_status(GiftReq.coop_identifier, GiftReq.contract_identifier, GiftReq.requesting_user_id).SerializeToString())
		except:
			return "", 404
	else:
		return "", 404

@app.route('/ei/leave_coop', methods=['POST'])
def ei_leave_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	LeaveCoopRequest = EIProto.LeaveCoopRequest()
	LeaveCoopRequest.ParseFromString(data)
	db_store.erase_coop_contribution(LeaveCoopRequest.coop_identifier, LeaveCoopRequest.contract_identifier, LeaveCoopRequest.player_identifier)
	return ""

@app.route('/ei/update_coop_permissions', methods=['POST'])
def ei_update_coop_permissions():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	PermUpdateReq = EIProto.UpdateCoopPermissionsRequest()
	PermUpdateReq.ParseFromString(data)
	PermUpdateResp = EIProto.UpdateCoopPermissionsResponse()
	BaseInfo = db_store.get_contract_info(PermUpdateReq.coop_identifier, PermUpateReq.contract_identifier)
	if BaseInfo[5] != PermUpdateReq.requesting_user_id:
		PermUpdateResp.success = False
		PermUpdateResp.message = "Only the co-op creator can change the permissions."
		return base64.b64encode(PermUpdateResp.SerializeToString())
	db_store.change_coop_public_state(PermUpdateReq.coop_identifier, PermUpdateReq.contract_identifier, PermUpdateReq.public)
	PermUpdateResp.success = True
	return base64.b64encode(PermUpdateResp.SerializeToString())

@app.route('/ei/<path:subpath>', methods=['POST'])
def ei_unidentified_routes(subpath):
	print("UNIMPLEMENTED REQ: /ei/" + subpath)
	if not request.form or "data" not in request.form:
		print("No data included in request")
		return "", 404
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	print("DATA", base64.b64encode(data))
	return "", 404


# /ei_data/ routes
@app.route('/ei_data/<path:subpath>', methods=['POST'])
def ei_data_rotues(subpath):
	print("REQ /ei_data/" + subpath)
	if subpath == "log_action":
		data = base64.b64decode(request.form["data"])
		GenericAction = EIProto.GenericAction()
		GenericAction.ParseFromString(data)
		print(GenericAction)
	else:
		print(request.form)
	return ""

# /ei_ps/ routes (custom)
# TODO: ratelimit this
@app.route('/ei_ps/<userid>/<method>', methods=['POST'])
def ei_ps_routes(userid, method):
	if True:
		return "Unimplemented.", 403
	# Valid userid?
	if len(userid) != 16:
		return "Invalid device ID format", 403
	# Do we have any backups tied to this user?
	Backups = db_store.get_backups(userid)
	if len(Backups) == 0:
		return "No such user found", 404
	SaveBackup = EIProto.Backup()
	SaveBackup.ParseFromString(zlib.decompress(base64.b64decode(Backups[-1][3])))
	if method == "break_piggy":
		if not SaveBackup.stats.piggy_full:
			return "Piggy Bank not full.", 403
		if time.time() - SaveBackup.stats.time_piggy_filled_realtime >= 604800:
			SaveBackup.stats.piggy_full = False
			SaveBackup.stats.piggy_found_full = False
			SaveBackup.stats.num_piggy_breaks += 1
			SaveBackup.stats.time_piggy_filled_realtime = 0.0
			SaveBackup.stats.time_piggy_full_gametime = 0.0
			SaveBackup.game.golden_eggs_earned += SaveBackup.game.piggy_bank
			# TODO: Recalc checksum - for now we know golden eggs earned trigger it
			SaveBackup.checksum += SaveBackup.game.piggy_bank
			# BEFORE ENABLING - Piggy bank doesn't reset, need to find a way to trigger that.
			SaveBackup.game.piggy_bank = 1
			SaveBackup.game.piggy_full_alert_shown = False
			db_store.update_backup(Backups[-1][0], base64.b64encode(zlib.compress(SaveBackup.SerializeToString())), True)
			return "Broke the piggy bank - accept the backup offer when restarting your game.", 200
		else:
			return "You need to have waited at least a week since filling the piggy bank before breaking it.", 403
	return "Unknown method", 404
