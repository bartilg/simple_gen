from azure.identity import InteractiveBrowserCredential
from azure.keyvault.secrets import SecretClient
import msal
import requests
import json

def print_json(json_data):
    """Pretty Prints json data

    Args:
        json_data (json): the json data to be printed
    """
    json_formatted_str = json.dumps(json_data, indent=2)
    print(json_formatted_str)

def get_vault_secret(tenant_id,vault_url,secret_name):
    """Gets a secret key from Azure Key Vault

    Args:
        tenant_id (string): the tenant id for the azure instance key vault is stored in
        vault_url (string): the url for azure key vault
        secret_name (string): the name for the desired secret

    Returns:
        string: the key pulled from Azure Key Vault
    """
    #Prompt for user login in browser
    credential = InteractiveBrowserCredential(tenant_id=tenant_id)
    #Pull client secret from azure key vault and return it
    client = SecretClient(vault_url=vault_url, credential=credential)
    retrieved_secret = client.get_secret(secret_name)
    return retrieved_secret.value

def get_access_token(client_id, authority, client_secret, scope):
    """Gets an access token for the MS Graph API

    Args:
        client_id (string): Application (client) ID from Azure App Registration
        authority (string): Authority url from the M365 Tenant
        client_secret (string): Client secret key from Azure App registration
        scope (string): Url for the scope permissions

    Returns:
        string: returns access token for MS Graph API
    """
    client = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    token_result = client.acquire_token_silent(scope, account=None)
    
    # If the token is available in cache, save it to a variable
    if token_result:
        access_token = token_result['access_token']
        print('Access token was loaded from cache')

    # If the token is not available in cache, acquire a new one from Azure AD and save it to a variable
    if not token_result:
        token_result = client.acquire_token_for_client(scopes=scope)
        print(token_result)
        access_token = token_result['access_token']
        print('New access token was acquired from Azure AD')

    return access_token

def paginate_json(data, headers, response_data):
    """Paginates Json API responses until hitting the end. Adds them to list response_data

    Args:
        data (json): response from initial API call
        headers (json): Headers for the API call
        response_data (list[json]): list of API return values
    """
    while "@odata.nextLink" in data:
        next_link = data["@odata.nextLink"]
        graph_result = requests.get(next_link, headers=headers)
        data = graph_result.json()
        response_data.extend(data["value"])

def patch_user(access_token, userPrincipalName, **kwargs):
    """Issues a PATCH request to update user properties in Azure AD
    For Valid PATCH arguments check API Reference: https://learn.microsoft.com/en-us/graph/api/user-update?view=graph-rest-1.0&tabs=http

    Args:
        access_token (string): access token for the MS Graph API
        userPrincipalName (string): UPN for the user to be patched
    """
    #MS Graph REST API url
    url = 'https://graph.microsoft.com/v1.0/users/' + userPrincipalName
    #Headers for API call (access token)
    headers = {
        'Authorization': access_token
    }    
    #init request body from kwargs key value pairs
    body = {}
    for key, value in kwargs.items():
        body[key] = value
    #Issue HTTP PATCH request to update user info
    temp = requests.patch(url,headers=headers,json=body)
    print(temp)

def create_user(access_token, userPrincipalName, password, **kwargs):
    #MS Graph REST API url
    url = 'https://graph.microsoft.com/v1.0/users/'
    #Headers for API call (access token)
    headers = {
        'Authorization': access_token
    }
    #init request body from kwargs key value pairs
    body = {}
    body['userPrincipalName'] = userPrincipalName
    body['usageLocation'] = 'US'
    my_pass = password
    body['passwordProfile'] = {
        "forceChangePasswordNextSignIn": False,
        "password": my_pass
    }
    
    #assign values from args
    for key, value in kwargs.items():
        body[key] = value
    print_json(body)
    #Issue HTTP PATCH request to update user info
    temp = requests.post(url,headers=headers,json=body)
    print(temp.content)
    return temp.content

def set_manager(access_token, user_upn, manager_upn):
    """Set a users manager

    Args:
        access_token (string): access token for the MS Graph API
        userPrincipalName (string): UPN for the user to be patched
        manager_id (string): The id of the user's manager
    """
    url = 'https://graph.microsoft.com/v1.0/users/' + user_upn + '/manager/$ref'
    headers = {
        'Authorization': access_token
    }
    body = {
        "@odata.id": "https://graph.microsoft.com/v1.0/users/" + manager_upn
    }
    temp = requests.put(url,headers=headers,json=body)
    print(temp)

def assign_license(access_token, userPrincipalName, license_sku_id):
    url = f'https://graph.microsoft.com/v1.0/users/{userPrincipalName}/assignlicense'
    print(url)
    headers = {
        'Authorization': access_token
    }
    body = {
        "addLicenses": [
            {
                "skuId": license_sku_id
            }
        ],
        "removeLicenses": []
    }
    temp = requests.post(url,headers=headers,json=body)
    print(temp)

def get_user_prefixes(access_token):
    """queries the Graph API and generates a Pandas Dataframe of all employees UPN's and Directory Id's

    Args:
        access_token (string): access token for the MS Graph API
    """
    url = 'https://graph.microsoft.com/v1.0/users?$select=userprincipalname'
    headers = {
        'Authorization': access_token
    }
    
    response_data = []
    
    # Make a GET request to the provided url, passing the access token in a header
    graph_result = requests.get(url=url, headers=headers)
    data = graph_result.json()
    response_data.extend(data["value"])

    paginate_json(data,headers,response_data)

    #convert to list of userPrincipalNames
    upn_list = [item['userPrincipalName'] for item in response_data]

    trimmed_upns = [email.split('@')[0] for email in upn_list]

    return trimmed_upns

def get_users_by_name(access_token,firstName,lastName):
    url = f"https://graph.microsoft.com/v1.0/users?$filter=(givenName eq '{firstName}' and surName eq '{lastName}')&$select=displayName,userPrincipalName,employeeId,mail,businessPhones,mobilePhone,department,jobTitle,officeLocation,companyName"
    headers = {
        'Authorization': access_token
    }
    
    response_data = []
    
    # Make a GET request to the provided url, passing the access token in a header
    graph_result = requests.get(url=url, headers=headers)
    data = graph_result.json()
    response_data.extend(data["value"])

    paginate_json(data,headers,response_data)
    return response_data

