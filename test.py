from api_tools import *
from sql_queries import *
import dotenv
import os
import sqlite3
import pyodbc
import struct
from sqlalchemy import create_engine

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


def test():
    #Get Access Token
    client_secret=get_vault_secret(tenant_id=os.getenv("TENANT_ID"), vault_url=os.getenv("VAULT_URL"),secret_name=os.getenv("VAULT_SECRET_NAME"))
    access_token = 'Bearer ' + get_access_token(os.getenv("CLIENT_ID"), os.getenv("AUTHORITY"),client_secret, [os.getenv("SCOPE")])
    db_token=get_access_token(os.getenv("CLIENT_ID"), os.getenv("AUTHORITY"),client_secret, [os.getenv("DB_SCOPE")])
    #return access_token
    conn = db_connect(db_token)
    print(load_existing_prefixes(conn))

test()