# azure-tools
Personal tools for working in Azure. Nothing too fancy, just a collection of what's' handy.

### aad-role-audit.py
Based on an az CLI session, determine if a user, group, or Service Principal has Entra ID / Azure AD role assignments (Directory or Custom), and deliver a final output with details. Does not yet include PIM.

### az-membership-enum.py
For a given CSV list of Azure users (exported from Azure portal or otherwise) collect AAD membership details using az ad CLI tools.

### graph-test-template.py
Convert an Azure CLI token to Graph, and make a query to a test MS Graph endpoint. Used as a base for quick prototyping and testing of Graph API endpoints.