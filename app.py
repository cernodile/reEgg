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
import db_store

upgrade_cache = {}

app = Flask(__name__)
contracts.load_contracts()
db_store.create_backups_db()
db_store.create_contracts_db()

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

@app.route('/ei/get_periodicals', methods=['POST'])
def ei_periodicals_request():
	PeriodicalResp = EIProto.PeriodicalsResponse()
	PeriodicalResp.contracts.warning_message = "Welcome to reEgg Server Emulator\nLeggacy contracts available every Monday/Friday"
	for evt in events.get_active_events():
		e = PeriodicalResp.events.events.add()
		e.CopyFrom(evt)
	for contract in contracts.get_active_contracts():
		c = PeriodicalResp.contracts.contracts.add()
		c.CopyFrom(contract)
	return base64.b64encode(PeriodicalResp.SerializeToString())

@app.route('/ei/query_coop', methods=['POST'])
def ei_query_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	QueryCoop = EIProto.QueryCoopRequest()
	QueryCoop.ParseFromString(data)
	QueryCoopResp = EIProto.QueryCoopResponse()
	db_query = db_store.is_coop_identifier_used(QueryCoop.coop_identifier)
	if db_query is not None:
		QueryCoopResp.exists = True
	else:
		QueryCoopResp.exists = False
	if QueryCoopResp.exists:
		if QueryCoop.league != db_query:
			QueryCoopResp.different_league = True
	# TODO: Ask contract defs for max coop allowed.
	#print(QueryCoopResp)
	return base64.b64encode(QueryCoopResp.SerializeToString())

@app.route('/ei/create_coop', methods=['POST'])
def ei_create_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	CreateCoop = EIProto.CreateCoopRequest()
	CreateCoop.ParseFromString(data)
	CreateResponse = EIProto.CreateCoopResponse()
	# Double check if in use
	db_query = db_store.is_coop_identifier_used(CreateCoop.coop_identifier)
	if db_query is not None:
		CreateResponse.success = False
		CreateResponse.message = "That co-op already exists."
		return base64.b64encode(CreateResponse.SerializeToString())
	# Can we identify the contract?
	contract = contracts.get_contract_by_identifier(CreateCoop.contract_identifier)
	if contract is None:
		CreateResponse.success = False
		CreateResponse.message = "Couldn't find your contract."
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

@app.route('/ei/coop_status', methods=['POST'])
def ei_coop_status():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	StatusReq = EIProto.ContractCoopStatusRequest()
	StatusReq.ParseFromString(data)
	StatusResp = EIProto.ContractCoopStatusResponse()
	# Get some base info (TODO: error handling)
	BaseInfo = db_store.get_contract_info(StatusReq.coop_identifier)
	ContribInfo = db_store.get_coop_contributors(StatusReq.coop_identifier)
	ContractInfo = contracts.get_contract_by_identifier(BaseInfo[2])
	TotalEggs = 0
	for x in ContribInfo:
		contributor = StatusResp.contributors.add()
		contributor.user_id = x[0]
		contributor.user_name = x[2]
		contributor.contribution_amount = x[4]
		TotalEggs += x[4]
		contributor.contribution_rate = x[5]
		contributor.soul_power = x[6]
		contributor.active = True
	StatusResp.coop_identifier = StatusReq.coop_identifier
	StatusResp.total_amount = TotalEggs
	StatusResp.auto_generated = False
	StatusResp.public = False
	StatusResp.creator_id = BaseInfo[5]
	StatusResp.seconds_remaining = (BaseInfo[4] + int(ContractInfo.length_seconds)) - int(time.time())
	return base64.b64encode(StatusResp.SerializeToString())

@app.route('/ei/update_coop_status', methods=['POST'])
def ei_update_coop_status():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	UpdateReq = EIProto.ContractCoopStatusUpdateRequest()
	UpdateReq.ParseFromString(data)
	db_store.update_coop_contribution(UpdateReq.coop_identifier, UpdateReq.user_id, UpdateReq.amount, UpdateReq.rate, UpdateReq.soul_power, UpdateReq.boost_tokens, UpdateReq.time_cheats_detected)
	Resp = EIProto.ContractCoopStatusUpdateResponse()
	Resp.finalized = True
	return base64.b64encode(Resp.SerializeToString())

@app.route('/ei/auto_join_coop', methods=['POST'])
def ei_auto_join_coop():
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	AutoJoinCoopRequest = EIProto.AutoJoinCoopRequest()
	AutoJoinCoopRequest.ParseFromString(data)
	print(AutoJoinCoopRequest)
	Resp = EIProto.JoinCoopResponse()
	Resp.success = False
	Resp.message = "Unable to find any public co-ops to join."
	return base64.b64encode(Resp.SerializeToString())

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
