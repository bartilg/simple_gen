import pandas as pd

def load_offices(conn):
    query = f"""--sql
        SELECT *
        FROM Offices
    """
    return pd.read_sql(query, conn)

def load_companies(conn):
    query = f"""--sql
        SELECT *
        FROM Companies
    """
    return pd.read_sql(query, conn)

def load_department_names(conn):
    query = f"""--sql
        SELECT Name
        FROM Departments
    """
    return pd.read_sql(query, conn)['Name'].tolist()

def load_existing_prefixes(conn):
    query = f"""--sql
        SELECT Prefix
        FROM Existing_Prefixes
    """
    return pd.read_sql(query,conn)['Prefix'].tolist()

def load_location_domains(conn):
    query = f"""--sql
        SELECT *
        FROM Location_Domains
    """
    return pd.read_sql(query, conn)

def load_locations(conn):
    query = f"""--sql
        SELECT *
        FROM Locations
    """
    return pd.read_sql(query, conn)