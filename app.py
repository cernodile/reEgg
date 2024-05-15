############
# Egg Inc v1.12.13 (Android Build 111121) server emulator
# Read the blog post at https://based.quest/reverse-engineering-a-mobile-app-protobuf-api/
############
import base64
import datetime
import time

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

@app.route('/ei/<path:subpath>', methods=['POST'])
def ei_routes(subpath):
	print("REQ: /ei/" + subpath)
	if subpath == "daily_gift_info":
		DateInfo = (datetime.datetime.now() - datetime.datetime(1970, 1, 1))
		GiftResponse = EIProto.DailyGiftInfo()
		GiftResponse.current_day = DateInfo.days
		GiftResponse.seconds_to_next_day = 86400 - DateInfo.seconds
		return base64.b64encode(GiftResponse.SerializeToString())
	data = base64.b64decode(request.form["data"].replace(" ", "+"))
	if subpath == "first_contact":
		ContactReq = EIProto.EggIncFirstContactRequest()
		ContactReq.ParseFromString(data)
		ContactResp = EIProto.EggIncFirstContactResponse()
		Backups = db_store.get_backups(ContactReq.user_id)
		if len(Backups) > 0:
			# Lets process backups - check for any forced ones first
			for backup in Backups:
				if backup[2] == True:
					# Force backup found - lets serialize the payload
					SaveBackup = EIProto.Backup()
					try:
						SaveBackup.ParseFromString(base64.b64decode(backup[3]))
						SaveBackup.force_backup = True
						SaveBackup.force_offer_backup = True
						ContactResp.backup.CopyFrom(SaveBackup)
						db_store.update_backup(backup[0], backup[3], False)
						break
					except:
						print("Failed to force serve backup - perhaps some logic error?")
						break
			# TODO: Check for soul eggs/eggs of prophecy and determine algorithm for "is it worth offering?"
		elif ContactReq.user_id in upgrade_cache:
			print("Found an unupgraded save - lets upgrade the permit level to Pro")
			ContactResp.backup.CopyFrom(cache[ContactReq.user_id])
			del upgrade_cache[ContactReq.user_id]
		return base64.b64encode(ContactResp.SerializeToString())
	elif subpath == "save_backup":
		SaveBackup = EIProto.Backup()
		SaveBackup.ParseFromString(bytes(data))
		#print(SaveBackup)
		if SaveBackup.game.permit_level == 0:
			SaveBackup.game.permit_level = 1
			SaveBackup.force_backup = True
			SaveBackup.force_offer_backup = True
			upgrade_cache[SaveBackup.user_id] = SaveBackup
		else:
			# start storing backups after permit upgrades
			db_store.add_backup(SaveBackup.user_id, request.form["data"].replace(" ", "+"))
	elif subpath == "get_periodicals":
		PeriodicalResp = EIProto.PeriodicalsResponse()
		for evt in events.get_active_events():
			e = PeriodicalResp.events.events.add()
			e.CopyFrom(evt)
		for contract in contracts.get_active_contracts():
			c = PeriodicalResp.contracts.contracts.add()
			c.CopyFrom(contract)
		return base64.b64encode(PeriodicalResp.SerializeToString())
	else:
		print("DATA", base64.b64encode(data))
	return ""

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
	SaveBackup.ParseFromString(base64.b64decode(Backups[-1][3]))
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
			db_store.update_backup(Backups[-1][0], base64.b64encode(SaveBackup.SerializeToString()), True)
			return "Broke the piggy bank - accept the backup offer when restarting your game.", 200
		else:
			return "You need to have waited at least a week since filling the piggy bank before breaking it.", 403
	return "Unknown method", 404
