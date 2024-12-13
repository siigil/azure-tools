############################
# Azure AD Role Audit
# Jan 2024
# Based on an az CLI session, determine if a user / group / SP has standard AAD role assignments (Directory or Custom), and deliver a final output with all group details. Does not yet include PIM.
# Notes:
# ./aad-role-audit.py -o [output file]
# Requires Directory.Read permissions
############################

import requests
import json
import subprocess
import argparse
import csv

typename_sp = "SPs"
endpoint_sp = "servicePrincipals"
typename_user = "Users"
endpoint_user = "users"
typename_group = "Groups"
endpoint_group = "groups"

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    ITAL = '\033[3m'
    LINK = '\033[4m'

# Fetch token for use during session, based on CLI authorization, in the format of a Graph token
def fetch_token():
    result = subprocess.run(["az","account","get-access-token","--resource-type","ms-graph"], stdout=subprocess.PIPE)
    output = result.stdout.decode("utf-8")
    token_data = json.loads(output)
    access_token = token_data["accessToken"]
    return access_token

# Progress Bar
def progress_bar(length,progress,psym="#",usym="-"):
    bar_length = 20
    progress = (progress) / length
    bar = psym * int(bar_length * progress)
    bar = bar.ljust(bar_length, usym)
    print(f"\r[-] {colors.OKBLUE}[{bar}]{colors.ENDC} {int(progress * 100)}%", end='')

# Make Graph API calls
def call(token, url):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    reply = response.json()
    return reply

# Collect Users
# using method in 74 & 75, return an error flag and then break later on.
def list_members(token,typename,endpoint,oid='',name=''):
    matches = True
    if oid:
        print(f"[-] Collecting {typename} with id \'{oid}\'.")
        url = f"https://graph.microsoft.com/v1.0/{endpoint}?$filter=id eq '{oid}'"
    elif name:
        print(f"[-] Collecting {typename} matching & starting with name term \'{name}\'.")
        url = f"https://graph.microsoft.com/v1.0/{endpoint}?$filter=startsWith(displayName,'{name}')"
    else:
        print(f"[-] Collecting all {typename}...")
        url = f"https://graph.microsoft.com/v1.0/{endpoint}"
    items = call(token,url)
    if not items.get('value',[]):
        print("[!] No matches found.")
        matches = False
    print(f"[-] {typename} found.")
    return items, matches

# Collect Roles
def list_roles(token,oid='',name=''):
    # Role Definition endpoint does not support filter, so need to filter client-side
    print("[-] Collecting Role(s)...")
    url = f"https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions?$select=displayName,id"
    roles = call(token,url)
    if oid:
        print(f"[+] Role ID: \'{oid}\'.")
        # Filter to just the role we're looking for
        i_role = [role for role in roles['value'] if role['id'] == oid]
        # Nest back into expected dictionary format
        roles = {'value': i_role}
    elif name:
        print(f"[+] Role Name Term: \'{name}\'.")
        n_role = [role for role in roles['value'] if role['displayName'].startswith(name)]
        roles = {'value': n_role}
    print("[-] Roles found.")
    return roles

# For Groups, enhance with Owners & *Groups* the Group is a MemberOf (this will be Group or sometimes Role details)
def list_group_owners_memberof(token,groups):
    print(f"[-] Fetching group details...")
    all_groups = groups.get('value',[])
    length = len(all_groups)

    for index, group in enumerate(all_groups):
        progress_bar(length, index + 1)

        # Prepare API URLs
        id = group['id']
        url = f"https://graph.microsoft.com/v1.0/groups/{id}/owners"
        url2 = f"https://graph.microsoft.com/v1.0/groups/{id}/memberof"

        # 1. Get Group Owners and add to groups
        group_owners=call(token,url)
        # Pull out list of owners for the group
        upns = [item['userPrincipalName'] for item in group_owners['value']]
        # Update the group item with the list of owners
        owners = {"owners": upns}
        group.update(owners)

        # 2. Get Group MemberOf and add to Groups
        group_memberof=call(token,url2)
        # Pull out list of owners for the group
        ids = [item['id'] for item in group_memberof['value']]
        displayName = [item['displayName'] for item in group_memberof['value']]
        # Update the group item with the list of owners
        groupMemberOfName = {"groupMemberOfName": displayName}
        groupMemberOfId = {"groupMemberOfId": ids}
        group.update(groupMemberOfName)
        group.update(groupMemberOfId)
    
    print("\n[-] Finished getting Group details.")
    return groups

# For Groups, enhance with members
def list_group_members(token,groups):
    print("[-] Collecting Group members...")
    # Prepare URL & query membership for each group
    for index, group in enumerate(groups['value']):
        id = group['id']
        url = f"https://graph.microsoft.com/v1.0/groups/{id}/members"
        members = call(token,url)
        # Gather group member details
        ids = [item['id'] for item in members['value']]
        names = [item['displayName'] for item in members['value']]
        upns = [item['userPrincipalName'] for item in members['value']]
        # Add group member details to each group
        group.update({"ids": ids})
        group.update({"names": names})
        group.update({"upns": upns})
    return groups

# For Roles, collect members
def get_role_members(roles, token):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    print(f"[-] Getting group membership of all roles...")
    all_roles = roles.get('value',[])
    length = len(all_roles)

    for index, role in enumerate(all_roles):
        progress_bar(length, index + 1)

        # Prepare API URL for role members
        # TODO: Make work with call() and return err from that method?
        id = role['id']
        url = f"https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments?$filter=roleDefinitionId eq '{id}'"
        roles_members = requests.get(url, headers=headers)
        try:
            roles_members.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if role['id'] == 'a0b1b346-4d3e-4e8b-98f8-753987be4970':
                pass
            else:
                print(f"\n[!] Role ID for '{role['displayName']}' ({role['id']}) not found ({err}). Skipping.")
            ids = []
        else:
            role_members = roles_members.json()
            # Pull out list of member-groups for the role
            ids = [item['principalId'] for item in role_members['value']]
            # Update the role item with the list of member-groups
        members = {"members": ids}
        role.update(members)
    return roles

# For Roles & Groups/Users, find matches
def find_member_roles(roles, objects, cat=''):
    print(f"\n[-] Finding {cat} role matches...")

    for obj in objects['value']:
    # Initialize group entries to store role match info
        obj.update({"roleNames":[]})
        obj.update({"roleIds":[]})

    # Set up roles for enumeration
    all_roles = roles.get('value',[])
    matches = False

    # For each role, check if any members match with our groups of interest. If so, add the corresponding role back to the group.
    for index, role in enumerate(all_roles):
        for member in role['members']:
            for obj in objects['value']:
                if member.strip() == obj['id'].strip():
                    # Print matches out so we know what's been found
                    print(f"[+] Role: {role['displayName']} ({role['id']}), Member: {obj['displayName']} ({obj['id']}).")
                    obj['roleNames'].append(role['displayName'])
                    obj['roleIds'].append(role['id'])
                    matches = True
    if matches == True:
        print(f"[+] {cat} role assignments were found.")
    elif matches == False:
        print(f"[!] No {cat} role assignments found.")
    return objects

# Prepare a CSV report of JSON data based on the provided Groups object & its members
def group_csv_report(groups, filename):
    with open(filename,'w') as csvfile:
        report = csv.writer(csvfile)
        report.writerow(['Group','UserId','UPN','Name'])
        for group in groups['value']:
            members = group['ids']
            upns = group['upns']
            names = group['names']
            for member, upn, name in zip(members,upns,names):
                report.writerow([group['displayName'],member,upn,name])

# Testing using for everything
def handle_item_roles(token, output, typename, endpoint, oid='', name=''):
    print(f"[-] Beginning {endpoint} role enumeration.")
    items,matches=list_members(token,typename,endpoint,oid,name)
    if not matches:
        print("[!] Quitting.")
        return
    roles=list_roles(token)
    roles=get_role_members(roles,token)
    items=find_member_roles(roles,items,typename)
    with open(f"{output}-{endpoint}.json",'w') as f:
        json.dump(items,f,indent=4)

def handle_roles(token, output, oid='', name=''):
    print("[-] Beginning role member enumeration.")
    # Gather users, groups, and target role
    users,matches=list_members(token,typename_user,endpoint_user)
    groups,matches=list_members(token,typename_group,endpoint_group)
    sps,matches=list_members(token,typename_sp,endpoint_sp)
    # Get roles, matching key terms if needed
    role=list_roles(token,oid,name)
    role=get_role_members(role,token)
    # Enrich members with role where applicable
    users=find_member_roles(role,users,typename_user)
    groups=find_member_roles(role,groups,typename_group)
    sps=find_member_roles(role,sps,typename_sp)
    if oid:
        roleschecked = oid
    if name:
        roleschecked = name
    else:
        roleschecked = "roles"
    with open(f"{output}-user-{roleschecked}.json",'w') as f:
        json.dump(users,f,indent=4)
    with open(f"{output}-group-{roleschecked}.json",'w') as f:
        json.dump(groups,f,indent=4)
    with open(f"{output}-sp-{roleschecked}.json",'w') as f:
        json.dump(sps,f,indent=4)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Python enumeration of Entra / Azure AD roles. Use to identify Entra ID / AAD permissions of users & groups. Does NOT enumerate Azure RBAC, only Azure AD/Entra roles.")
    parser.add_argument('--output', '-o', type=str, help='Output file name, instead of stdout')
    parser.add_argument('--users', '-u', action='store_true', help='Gather user AAD roles, use name (-n) or id (-i) to filter.',required=False)
    parser.add_argument('--groups', '-g', action='store_true', help='Gather group AAD roles, use name (-n) or id (-i) to filter.',required=False)
    parser.add_argument('--sp', '-s', action='store_true', help='Gather SP AAD roles, use name (-n) or id (-i) to filter.',required=False)
    parser.add_argument('--all', '-a', action='store_true', help='Gather group + user AAD roles',required=False)
    parser.add_argument('--name', '-n', type=str, help='Full or partial Group or User display name',required=False)
    parser.add_argument('--oid', '-i', type=str, help='Known ID of Group or User',required=False)
    parser.add_argument('--role', '-r', action='store_true', help='Gather users/groups of a known role, use name (-n) or id (-i).',required=False)
    args = parser.parse_args()

    # Gather session token
    token = fetch_token()

    # Verify search and name are not both set

    if not args.output:
        args.output = "output"

    if args.users == True:
        handle_item_roles(token,args.output,typename_user,endpoint_user,args.oid,args.name)

    elif args.groups == True:
        handle_item_roles(token,args.output,typename_group,endpoint_group,args.oid,args.name)

    elif args.sp == True:
        handle_item_roles(token,args.output,typename_sp,endpoint_sp,args.oid,args.name)

    elif args.all == True:
        handle_item_roles(token,args.output,typename_user,endpoint_user,args.oid,args.name)
        handle_item_roles(token,args.output,typename_group,endpoint_group,args.oid,args.name)
        handle_item_roles(token,args.output,typename_sp,endpoint_sp,args.oid,args.name)
        
    elif args.role == True:
        handle_roles(token,args.output,args.oid,args.name)

    else:
        print("[!] Please specify --users or --groups, or -h for help.")

if __name__ == "__main__":
    main()