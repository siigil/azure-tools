# azure-tools
Personal tools for working in Azure. Nothing too fancy, just a collection of what's handy.

## aad-role-audit.py
Based on an az CLI session, determine if a User, Group, or Service Principal has current Entra ID / Azure AD role assignments (Directory or Custom), and deliver a final output with details:
- Return results based on Group, User, SP, or Role
- Options for name (-n) and id (-i) matching
- Current results returned in JSON (-o) and CLI findings
### Examples:
#### Return role assignments for groups starting with term "Test"
`python3 aad-role-audit.py -gn "Test"`
#### Return role assignments for "Global" roles ("Global Administrator", "Global Reader")
`python3 aad-role-audit.py -rn "Global"`
#### Return role assignments for users starting with "Z" in a file "2024-03-users.json" (default is output-users.json)
`python3 aad-role-audit.py -un Z -o 2024-03`
#### Return role assignments for "Global Reader" by role ID (can be used with users, groups, & SPs as well)
`python3 aad-role-audit.py -ri f2ef992c-3afb-46b9-b7cf-a126ee74c451`

## az-membership-enum.py
For a given CSV list of Azure users (exported from Azure portal or otherwise) collect AAD membership details using az ad CLI tools.

## graph-test-template.py
Convert an Azure CLI token to Graph, and make a query to a test MS Graph endpoint. Used as a base for quick prototyping and testing of Graph API endpoints.
