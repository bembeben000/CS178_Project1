import pymysql
import pymysql.cursors  
import creds             
import boto3           

# ------------------------------------------
# Establish a Connection to MySQL Database
# ------------------------------------------
def get_conn():
    """
    Creates and returns a connection to the MySQL database using credentials 
    provided in the `creds` module. The cursor returns results as dictionaries.
    """
    return pymysql.connect(
        host=creds.host,
        user=creds.user,
        password=creds.password,
        db=creds.db,
        cursorclass=pymysql.cursors.DictCursor  # Makes results easier to work with using column names
    )

# ------------------------------------------
# Execute a Query and Return Results
# ------------------------------------------
def execute_query(query, args=()):
    """
    Executes a given SQL query with optional arguments and returns the result as a list of dictionaries.
    Ensures the connection is closed after execution, even if an error occurs.
    
    Parameters:
        query (str): SQL query string to execute.
        args (tuple): Optional tuple of arguments to safely pass into the query.
        
    Returns:
        list[dict]: Query results where each row is a dictionary.
    """
    conn = get_conn()  # Establish connection
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)  # Execute SQL with parameters
            rows = cur.fetchall()     # Fetch all rows of the result
        return rows
    finally:
        conn.close() 
