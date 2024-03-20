# For a given CSV list of Azure users (exported from Azure portal or otherwise) on Mac/Linux using az ad CLI tools, collect AAD membership details.

# az-membership-enum.py <list of users>
import json
import sys
import subprocess
import json

output = 'results.csv'

# for each user in list of input
input = open(sys.argv[1], 'r')
usrs = input.readlines()
o = open(output, "a")
for line in usrs:

	# enumerate user group information from aad
	usr = line.encode('utf-8').strip() 
	print(usr)
	cmd = ['az', 'ad', 'user', 'get-member-groups', '--id', usr]
	groups = subprocess.Popen(cmd, stdout=subprocess.PIPE)
	out, err = groups.communicate()
	resp = json.loads(out)
	for i in resp:
		grp = i['displayName']
		id = i['objectId']
		line = usr+","+grp.encode('utf-8').strip()+","+id.encode.encode('utf-8').strip()+"\n"

		# append a line for each membership entry to a rolling csv
		o.write(line)
o.close()
