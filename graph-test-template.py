############################
# Microsoft Graph Query Test Template
# Jan 2024
# Convert an Azure CLI token to Graph, and make a query to a test MS Graph endpoint.
# Used for prototyping and testing APIs.
# Notes: ./graph-test-template.py
############################

import requests
import json
import subprocess

# Fetch token for use during session, based on CLI authorization, in the format of a Graph token (won't work otherwise)
def fetch_token():
    result = subprocess.run(["az","account","get-access-token","--resource-type","ms-graph"], stdout=subprocess.PIPE)
    output = result.stdout.decode("utf-8")
    token_data = json.loads(output)
    access_token = token_data["accessToken"]
    return access_token

def testcommand(token):
    # Modify the below on the fly to line up with what endpoint you'd like to test out.
    name = 'Bob'
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=displayName eq '{name}'"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    reply = response.json()
    return reply

access_token = fetch_token()
reply=testcommand(access_token)
print(reply)

# If you need file output:
#with open(f"test-output.json", 'w') as f:
#    json.dump(reply, f, indent=4)