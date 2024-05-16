# db_store.py - Providing "cloud saves" and such
import sqlite3
import time

# TODO: Truncate last x backups from a given device ID
def get_connection(dbName):
	con = sqlite3.connect("db/" + dbName + ".db")
	return con

def create_backups_db():
	FreshInstall = True
	con = get_connection("backups")
	cur = con.cursor()
	try:
		cur.execute("CREATE TABLE Backups(BackupID INTEGER PRIMARY KEY AUTOINCREMENT, DeviceID TEXT, BackupStamp BIGINT, ForceOffer BOOL, Payload TEXT)")
	except:
		FreshInstall = False
	con.commit()
	con.close()
	return FreshInstall

def get_backup(ref_id):
	if not isinstance(ref_id, int):
		return None
	con = get_connection("backups")
	cur = con.cursor()
	res = cur.execute("SELECT Payload FROM Backups WHERE BackupID=" + str(ref_id))
	tuple = res.fetchone()
	con.close()
	if tuple is None:
		return tuple
	else:
		return tuple[0]

def cleanup_backups(numids):
	con = get_connection("backups")
	cur = con.cursor()
	cur.execute("DELETE FROM Backups WHERE BackupID IN(" + (", ".join(map(str, numids))) + ")")
	con.commit()
	con.close()
	return

def get_backups(device_id):
	if not device_id.isalnum():
		return []
	con = get_connection("backups")
	cur = con.cursor()
	res = cur.execute("SELECT BackupID, BackupStamp, ForceOffer, Payload FROM Backups WHERE DeviceID=\"" + device_id + "\"")
	x = res.fetchall()
	con.close()
	if x is None:
		return []
	else:
		return x

def get_last_backup(device_id):
	if not device_id.isalnum():
		return None
	con = get_connection("backups")
	cur = con.cursor()
	res = cur.execute("SELECT BackupID, BackupStamp, ForceOffer, Payload FROM Backups WHERE DeviceID=\"" + device_id + "\" ORDER BY BackupID DESC LIMIT 1")
	x = res.fetchall()
	con.close()
	if x is None:
		return []
	else:
		return x[0]

def add_backup(device_id, b64str):
	if not device_id.isalnum():
			return
	con = get_connection("backups")
	cur = con.cursor()
	stamp = int(time.time())
	res = cur.execute("INSERT INTO Backups(DeviceID, BackupStamp, ForceOffer, Payload) VALUES(?, ?, ?, ?)", (device_id, stamp, False, b64str))
	con.commit()
	con.close()
	return

def update_backup(refID, b64str, Force):
	con = get_connection("backups")
	cur = con.cursor()
	res = cur.execute("UPDATE Backups SET ForceOffer=?, Payload=? WHERE BackupID=" + str(refID), (Force, b64str))
	con.commit()
	con.close()
	return

def offer_backup_id_to_new_device(refID, device_id):
	srcBackup = get_backup(refID)
	if srcBackup is None:
		return
	add_backup(device_id, srcBackup)
	return

# If you used my server prior to zlib saves, uncomment and run once.
#import zlib
#import base64
#def compress_to_zlib():
#	con = get_connection("backups")
#	cur = con.cursor()
#	res = cur.execute("SELECT BackupID, ForceOffer, Payload FROM Backups");
#	x = res.fetchall()
#	con.close()
#	for backup in x:
#		print(backup[0])
#		update_backup(backup[0], base64.b64encode(zlib.compress(base64.b64decode(backup[2]))), backup[1])
#compress_to_zlib()

## MANUAL TRANSFER EXAMPLE
## TODO: Admin API endpoint for this
# offer_backup_id_to_new_device(2, "f7c9c95ce5f6d06a")
