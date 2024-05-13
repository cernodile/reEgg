############
# Egg Inc v1.12.13 (Android Build 111121) server emulator
# Read the blog post at https://based.quest/reverse-engineering-a-mobile-app-protobuf-api/
############
import base64
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
		print(request.form)
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
