# is it a hexadecimal identifier with 16 length
def is_valid_username(str):
	if len(str) != 16:
		return False
	try:
		int(str, 16)
		return True
	except:
		return False

# validate alphanumeric + dashes
def is_valid_coop_or_contract(str):
	for char in str:
		if not (char.isalnum() or char == '-'):
			return False
	return True

# is it 1-20 chars long, alphanumeric + dasher, underscores, spaces and brackets
def is_valid_display_name(str):
	str = str.strip()
	length = len(str)
	if length == 0 or length > 20:
		return False
	for char in str:
		if not char.isalnum():
			if char in '-_[]() ':
				continue
			return False
	return True
