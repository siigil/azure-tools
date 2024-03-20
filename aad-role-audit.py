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
    print(f"\r{colors.OKBLUE}[{bar}]{colors.ENDC} {int(progress * 100)}%", end='')

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
def list_users(token,oid='',name=''):
    if oid:
        print(f"{colors.ITAL}Collecting User with id \'{oid}\'.{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/users?$filter=id eq '{oid}'"
    elif name:
        print(f"{colors.ITAL}Collecting Users with name \'{name}\'.{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/users?$filter=displayName eq '{name}'"
    else:
        print(f"{colors.ITAL}Collecting all Users...{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/users"
    users = call(token,url)
    print(users)
    return users

# Collect Groups
def list_groups(token,oid='',name=''):
    if oid:
        print(f"{colors.ITAL}Collecting Group with id \'{oid}\'.{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/groups?$filter=id eq '{oid}'"
    elif name:
        print(f"{colors.ITAL}Collecting Groups with name \'{name}\'.{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '{name}'"
    else:
        print(f"{colors.ITAL}Collecting all Groups...{colors.ENDC}")
        url = f"https://graph.microsoft.com/v1.0/groups"
    groups = call(token,url)
    return groups

# Collect Service Principals
def list_sps(token,oid='',name=''):
    if oid:
        print(f"{colors.ITAL}Collecting SP with id \'{oid}\'.{colors.ITAL}")
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=id eq '{oid}'"
    elif name:
        print(f"{colors.ITAL}Collecting SPs with name \'{name}\'.{colors.ITAL}")
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=displayName eq '{name}'"
    else:
        print(f"{colors.ITAL}Collecting all SPs...{colors.ITAL}")
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals"
    sps = call(token,url)
    return sps

# Collect Roles
def list_roles(token,oid='',name=''):
    # Role Definition endpoint does not support filter, so need to filter client-side
    print("\x1B[3mCollecting Role(s)...\x1B[0m", end =' ')
    url = f"https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions?$select=displayName,id"
    roles = call(token,url)
    if oid:
        print(f"\x1B[3mRole ID: \'{oid}\'.\x1B[0m")
        # Filter to just the role we're looking for
        i_role = [role for role in roles['value'] if role['id'] == oid]
        # Nest back into expected dictionary format
        roles = {'value': i_role}
    elif name:
        print(f"\x1B[3mRole Name: \'{name}\'.\x1B[0m")
        n_role = [role for role in roles['value'] if role['displayName'] == name]
        roles = {'value': n_role}
    return roles

# For Groups, enhance with Owners & *Groups* the Group is a MemberOf (this will be Group or sometimes Role details)
def list_group_owners_memberof(token,groups):
    print("Fetching group details...")
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
    
    print("\nFinished getting Group details.")
    return groups

# For Groups, enhance with members
def list_group_members(token,groups):
    print("Collecting Group members...")
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
    print("Getting group membership of all roles...")
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
            print(f"\nRole ID for '{role['displayName']}' ({role['id']}) not found ({err}). Skipping.")
            ids = []
        else:
            role_members = roles_members.json()
            # Pull out list of member-groups for the role
            ids = [item['principalId'] for item in role_members['value']]
            # Update the role item wiht the list of member-groups
        members = {"members": ids}
        role.update(members)
    return roles

# For Roles & Groups/Users, find matches
def find_member_roles(roles, objects, cat=''):
    print(f"\nFinding {cat} role matches...")

    for obj in objects['value']:
        # Initialize group entries to store role match info
        obj.update({"roleNames":[]})
        obj.update({"roleIds":[]})
    
    # Set up roles for enumeration
    all_roles = roles.get('value',[])
    matches = False

    # For each role, check if any members match with our groups of interest. If so, add the corresponding role back to the group.
    for index, role in enumerate(all_roles):
        #progress_bar(length,index+1)
        for member in role['members']:
            for obj in objects['value']:
                if member.strip() == obj['id'].strip():
                    # Print matches out so we know what's been found
                    print(f"Role: {role['displayName']} ({role['id']}), Member: {obj['displayName']} ({obj['id']}).")
                    obj['roleNames'].append(role['displayName'])
                    obj['roleIds'].append(role['id'])
                    matches = True
    if matches == True:
        print(f"{cat} role assignments were found.")
    elif matches == False:
        print(f"No {cat} role assignments found.")
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
    csvfile.close()

def handle_user_roles(token, output, oid='', name=''):
    print("Beginning user role enumeration.")
    users=list_users(token,oid,name)
    roles=list_roles(token)
    roles=get_role_members(roles,token)
    users=find_member_roles(roles,users,"User")
    with open(f"{output}-users.json",'w') as f:
        json.dump(users,f,indent=4)

def handle_sp_roles(token, output, oid='', name=''):
    print("Beginning SP role enumeration.")
    sps=list_sps(token,oid,name)
    roles=list_roles(token)
    roles=get_role_members(roles,token)
    users=find_member_roles(roles,sps,"SP")
    with open(f"{output}-sps.json",'w') as f:
        json.dump(users,f,indent=4)

def handle_group_roles(token, output, oid='', name=''):
    print("Beginning group role enumeration.")
    groups=list_groups(token,oid,name)
    groups=list_group_owners_memberof(token,groups)
    roles=list_roles(token)
    roles=get_role_members(roles,token)
    groups=find_member_roles(roles,groups,"Group")
    with open(f"{output}-groups.json",'w') as f:
        json.dump(groups,f,indent=4)

def handle_roles(token, output, oid='', name=''):
    print("Beginning role member enumeration.")
    # Gather users, groups, and target role
    users=list_users(token)
    groups=list_groups(token)
    role=list_roles(token,oid,name)
    role=get_role_members(role,token)
    users=find_member_roles(role,users,"User")
    groups=find_member_roles(role,groups,"Group")
    
    with open(f"{output}-roles.json",'w') as f:
        json.dump(users,f,indent=4)

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

    if args.users == True:
        handle_user_roles(token,args.output,args.oid,args.name)

    elif args.groups == True:
        handle_group_roles(token,args.output,args.oid,args.name)

    elif args.sp == True:
        handle_sp_roles(token,args.output,args.oid,args.name)

    elif args.all == True:
        handle_user_roles(token,args.output,args.oid,args.name)
        handle_group_roles(token,args.output,args.oid,args.name)
        handle_sp_roles(token,args.output,args.oid,args.name)
        
    elif args.role == True:
        handle_roles(token,args.output,args.oid,args.name)

    else:
        print("Please specify --users or --groups, or -h for help.")

if __name__ == "__main__":
    main()

############################
# Future Possible Features: 
# - Add PIM functionality - Can't check for PIM roles without additional assignmetns in the Graph API (api.azrbac.mspim.azure.com is not available to users)
# - Save the Roles as a DB & import
# - Smooth reporting functionality - default = CLI, otherwise JSON dump or report - set whether to list all matches or not
# - Get fields for dynamic groups and put into final report
# - Prettier output
# - [Later] Token loading methods, vs just 'az auth'.