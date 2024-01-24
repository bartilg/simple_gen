from api_tools import *
from sql_queries import *
import dotenv
import os
import string
import random
import struct
import csv
import pyodbc
from sqlalchemy import create_engine
import sqlite3
import copy

dotenv.load_dotenv()

def pad_token(access_token):
    """Pads MSAL access token for compatibility with MS SQL Server in Azure.
    Further explanation of this issue can be found here.
    https://github.com/AzureAD/azure-activedirectory-library-for-python/wiki/Connect-to-Azure-SQL-Database
    https://github.com/mkleehammer/pyodbc/issues/228

    Args:
        access_token (string): Access Token returned by MSAL

    Returns:
        bytes: Byte packed access token
    """
    #Convert Token to Bytes
    tokenb = bytes(access_token, "UTF-8")
    exptoken = b''
    for i in tokenb:
        exptoken += bytes({i})
        exptoken += bytes(1)
    tokenstruct = struct.pack("=i", len(exptoken)) + exptoken
    return tokenstruct

def az_db_connect(driver,server,database,access_token):
    """Establishes a connection to an Azure SQL database using an access token

    Args:
        driver (String): String describing the ODBC Driver to use for the connection
        server (String): url and port for the SQL Server
        database (database): Name of the Database to access on the SQL Server
        access_token (string): access token to authenticate with the sql server

    Returns:
        _type_: _description_
    """
    #Build ODBC connection string
    azure_conn_str = (
    f"Driver={driver};"
    f"Server={server};"
    f"Database={database};"
    )
    
    #Pad Token for compatibility
    padded_token = pad_token(access_token)
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    #Establish Connection
    azure_conn = pyodbc.connect(azure_conn_str, attrs_before = { SQL_COPT_SS_ACCESS_TOKEN:padded_token })
    engine= create_engine('mssql+pyodbc://',creator=lambda: azure_conn)
    return engine


def db_connect(access_token):
    """ Establishes a connection to a database described in the environment

    Args:
        access_token (string): access token for Microsoft Graph

    Raises:
        Exception: Throws an exception if the Database type is invalid

    Returns:
        Connection: Database connection objects
    """
    mode = os.getenv("DB_MODE")
    match mode:
        case "SQLITE":
            return sqlite3.connect(os.getenv("DB_PATH"))
        case "AZURE":
            return az_db_connect(os.getenv("DB_DRIVER"),os.getenv("DB_SERVER"),os.getenv("DB_DATABASE"),access_token)
        case _:
            raise Exception("Invalid Database Mode")

def prompt_user(question):
    """Prompts user for a yes or no question. Defaults to Yes if no input

    Args:
        question (string): The question to be asked

    Returns:
        bool: returns True if the users ansers yes, False if no
    """
    user_input = input(f"{question} [Y/n]: ")
    match user_input.lower():
        case "y"|"yes"|"":
            return True
        case "n"|"no":
            return False
        case _:
            print("Invalid Input\n")
            return prompt_user(question)
        
def gen_password():
    """Generates a random password with w format of 1 Upper, 3 Lower, 5 Num, 1 Special

    Returns:
        string: The randomely generated password
    """
    uppercase_letter = random.choice(string.ascii_uppercase)
    lowercase_letters = ''.join(random.choices(string.ascii_lowercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=5))
    special_character = random.choice('!@#$%^&*()')
    
    matching_string = uppercase_letter + lowercase_letters + numbers + special_character
    
    return matching_string

def dict_to_csv(csv_path, dict, col1='Key',col2='Value'):
    """Writes a dictionary to a csv file, column 1 is the keys, and column 2 is the valuesd

    Args:
        csv_path (string): path for the csv file to write to
        dict (dictionary): dictionary to write to csv
        col1 (string): name for column 1 header
        col2 (string): name for column 2 header
    """
    # Open the CSV file in write mode
    with open(csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write the header (column names)
        writer.writerow([col1, col2])
        # Write the data
        for key, value in dict.items():
            writer.writerow([key, value])

def gen_prefix(first_name,last_name, existing_prefixes):
    """Generates a unique email prefix

    Args:
        first_name (String): Users First Name
        last_name (String): Users Last Name
        existing_prefixes (list): a list of prefixes that have already been used

    Returns:
        string: a new unique email prefix
    """
    #define the 3 conventions: first initial last name, first name last initial, first name last name
    pref_1 = lambda a,b,c : a[0].lower() + b.lower() + c
    pref_2 = lambda a,b,c : a.lower() + b[0].lower() + c
    pref_3 = lambda a,b,c : a.lower() + b.lower() + c
    iter = ''

    #iterate until unique prefix is found, then break
    while True:
        if (pref_1(first_name,last_name,iter)) not in existing_prefixes:
            result = pref_1(first_name,last_name,iter)
            break
        elif (pref_2(first_name,last_name,iter)) not in existing_prefixes:
            result = pref_2(first_name,last_name,iter)
            break
        elif (pref_3(first_name,last_name,iter)) not in existing_prefixes:
            result = pref_3(first_name,last_name,iter)
            break
        elif iter == '':
            #begin adding iterators after first loop
            iter = '1'
        else:
            iter = str(int(iter)+1)

    return result

def iter_users(access_token, users_path, pass_path, prefixes, conn):
    #read contents into pandas dataframes
    user_df = pd.read_csv(users_path)

    dept_names = load_department_names(conn)

    office_df = load_offices(conn)
    company_df = load_companies(conn)

    pass_dict = {}

    for index, row in user_df.iterrows():
        prefix = gen_prefix(row['firstName'], row['lastName'], prefixes)
        #Generate UPN
        userPrincipalName = prefix + '@championsgh.com'
        #Generate Email Address
        send_domain = company_df.loc[company_df['Abbreviation'] == row['companyAbbreviation'], 'Domain'].values[0]
        companyName = company_df.loc[company_df['Abbreviation'] == row['companyAbbreviation'], 'Name'].values[0]
        #Set defaults for manager and licenses
        manager = "NULL"

        #Mandatory Fields: firstName, lastName, companyName        
        args = {
            'mailNickname': prefix,
            'mail' : prefix + '@' + send_domain,
            'givenName' : row['firstName'],
            'surname' : row['lastName'],
            'companyName' : companyName,
            'accountEnabled': True
        }
        #Loop other values, skipping null
        for column, value in row.items():
            if str(value) != 'nan':
                match column:
                    case "firstName"|"lastName"|"companyAbbreviation":
                        pass
                    case "officePhone":
                        args.update({'businessPhones' : [row[column]]})
                    case "officeOrField":
                        args.update({'onPremisesExtensionAttributes': {'extensionAttribute1':row['officeOrField']}})
                    case "department":
                        if row[column] not in dept_names:
                            print("Invalid Department")
                            return
                        args.update({column: str(value)})
                    case "Office":
                        args.update({'officeLocation' : row[column], 
                            'streetAddress': office_df.loc[office_df['Office'] == row['Office'], 'Address'].values[0],
                            'city' : office_df.loc[office_df['Office'] == row['Office'], 'City'].values[0],
                            'country' : office_df.loc[office_df['Office'] == row['Office'], 'Country'].values[0],
                            'state' : office_df.loc[office_df['Office'] == row['Office'], 'State'].values[0],
                            'postalCode' : str(office_df.loc[office_df['Office'] == row['Office'], 'Zip'].values[0])})
                    case "manager":
                        #cache manager value since its
                        manager=row['manager']
                    case _:
                        args.update({column: str(value)})

        #Get a list of users with the same first and last name
        potential_dupes = get_users_by_name(access_token=access_token,firstName=args['givenName'],lastName=args['surname'])

        #If there are potential duplicates, prompt the user if they are certain they want to create the account
        if len(potential_dupes) > 0:
            print("The following users may already exist:\n")
            print_json(potential_dupes)
            if not prompt_user("Are you sure this isn't a duplicate? "):
                print(f"Skipping User: {args['givenName']} {args['surname']}")
                continue

        #Generate the password and create the user
        n_pass = gen_password()
        create_user(access_token,userPrincipalName, n_pass, **args)        
        prefixes.append(prefix)
        pass_dict.update({userPrincipalName:n_pass})

        #Set user manager
        if(manager != "NULL"):
            set_manager(access_token,userPrincipalName,manager)

    dict_to_csv(pass_path, pass_dict)

def run():
    #Get Access Token for Graph API
    client_secret=get_vault_secret(tenant_id=os.getenv("TENANT_ID"), vault_url=os.getenv("VAULT_URL"),secret_name=os.getenv("VAULT_SECRET_NAME"))
    access_token = 'Bearer ' + get_access_token(os.getenv("CLIENT_ID"), os.getenv("AUTHORITY"),client_secret, [os.getenv("SCOPE")])
    #Get Access token for DB Access and establish connection
    db_token=get_access_token(os.getenv("CLIENT_ID"), os.getenv("AUTHORITY"),client_secret, [os.getenv("DB_SCOPE")])
    conn = db_connect(db_token)
    #Load prefixes from db
    prefixes = [item.lower() for item in load_existing_prefixes(conn)]
    #create copy to diff later
    old_prefixes = copy.deepcopy(prefixes)
    #add prefixes from M365 and remove duplicates
    prefixes += [item.lower() for item in get_user_prefixes(access_token)] 
    #remove duplicates
    uniq_prefixes = set(prefixes)
    prefixes = list(uniq_prefixes)
    
    iter_users(access_token, os.getenv("USER_PATH"), os.getenv("PASS_PATH"), prefixes, conn)

    new_prefixes = set(prefixes) - set(old_prefixes)

    # Identify new values
    new_prefixes = [value for value in new_prefixes if value not in old_prefixes]
    #Add new prefixes to database
    new_pref_df = pd.DataFrame({'Prefix':new_prefixes})
    new_pref_df.to_sql('Existing_Prefixes', conn, if_exists='append', index=False)

run()
