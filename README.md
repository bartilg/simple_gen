
# SimpleGen Onboarding Script

## Windows Installation 
1. In order to install you must have Python installed. 
2. To install Python use the following PowerShell command:   
    ```PowerShell
    winget install Python.python.3.12
    ```
3. Upon first run, open the root folder of the project in the terminal, and run the following command:
    ```PowerShell
    pip install -r requirements.txt
    ```
    This will install the necessary dependancies.
    
4. You must also Install the Microsoft ODBC Driver to connect the the sql database: [Download MS ODBC Here](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16)
   
## How to Use
1. Edit the information for the users you would like to create in **user_list.csv**
2. Make sure you save user_list.csv before running the script
3. Open your terminal in the root directory and run the script with the following command:
    ```PowerShell
    Python simple_gen.py
    ```

- Columns are provided for valid fields
- Passwords for the created users are output to **password_cache.csv**
- As new Brands are added, tables in the database may need to be updated for validation purposes

## Additional Notes
- Script is designed to be used with Azure Key Vault for Authentication
- Key Vault and tenant are assumed to be the same