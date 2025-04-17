from flask import Flask, render_template, request, redirect, url_for
import pymysql
import creds
from dbCode import * 
import boto3

# Connect to DynamoDB and access the 'Countries' table for user authentication
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
user_table = dynamodb.Table('Countries')

# Initialize Flask app
app = Flask(__name__)

# ------------------------------------------
# SQL Function: Retrieve countries with optional name filtering
# ------------------------------------------
def get_filtered_countries(country_name=None):
    """
    Fetch country data from MySQL database, optionally filtering by country name.
    Only includes countries where the language is marked as official.
    """
    base_query = """
        SELECT c.Name, c.Continent, c.Region, c.Population, c.Capital, 
               c.GovernmentForm, c.GNP, cl.Language
        FROM country c
        JOIN countrylanguage cl ON c.Code = cl.CountryCode
        WHERE cl.IsOfficial = 'T'
    """
    if country_name:
        base_query += " AND c.Name LIKE %s LIMIT 15;"
        return execute_query(base_query, (f"%{country_name}%",))
    else:
        base_query += " LIMIT 15;"
        return execute_query(base_query)

# ------------------------------------------
# Route: User Authentication (Login/Signup)
# ------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def auth():
    """
    Displays login/signup form and processes user authentication.
    Data is stored in DynamoDB.
    """
    message = ""
    if request.method == 'POST':
        action = request.form['action']
        username = request.form['username']
        password = request.form['password']

        if action == 'signup':
            # Check if user already exists
            existing_user = user_table.get_item(Key={'Name': username})
            if 'Item' in existing_user:
                message = "Username already exists. Please choose another."
            else:
                # Add new user to DynamoDB
                user_table.put_item(Item={'Name': username, 'Password': password})
                message = "Signup successful! You can now log in."

        elif action == 'login':
            # Validate user credentials
            user = user_table.get_item(Key={'Name': username})
            if 'Item' in user and user['Item']['Password'] == password:
                return redirect(url_for('sql'))
            else:
                message = "Invalid username or password."

    return render_template('dynamo.html', message=message)

# ------------------------------------------
# Route: SQL Country Search Interface
# ------------------------------------------
@app.route('/sql', methods=['GET', 'POST'])
def sql():
    """
    Displays an interface to search and filter countries using SQL.
    User must be logged in to access this.
    """
    message = ""
    results = []

    if request.method == 'POST':
        action = request.form['action']
        if action == 'search':
            # Get countries matching user input
            country_name = request.form['country']
            results = get_filtered_countries(country_name)
            if not results:
                message = f"No results found for '{country_name}'."
        elif action == 'reset':
            # Reset to show initial results
            results = get_filtered_countries()
    else:
        results = get_filtered_countries()

    return render_template('index.html', results=results, message=message)

# ------------------------------------------
# Route: Update User Password
# ------------------------------------------
@app.route('/update-password', methods=['GET', 'POST'])
def update_password():
    """
    Allows users to update their password by verifying the old password first.
    """
    message = ""
    if request.method == 'POST':
        username = request.form['username']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        # Verify user and current password
        response = user_table.get_item(Key={'Name': username})
        if 'Item' not in response:
            message = "User not found."
        elif response['Item']['Password'] != old_password:
            message = "Old password is incorrect."
        else:
            # Update password in DynamoDB
            user_table.update_item(
                Key={'Name': username},
                UpdateExpression='SET Password = :newpw',
                ExpressionAttributeValues={':newpw': new_password}
            )
            message = "Password updated successfully!"

    return render_template('update_password.html', message=message)

# ------------------------------------------
# Route: Delete User Account
# ------------------------------------------
@app.route('/delete-account', methods=['POST'])
def delete_account():
    """
    Deletes a user account from DynamoDB after password confirmation.
    """
    username = request.form['username']
    password = request.form['password']

    # Verify credentials before deletion
    user = user_table.get_item(Key={'Name': username})
    if 'Item' not in user:
        message = "User not found."
    elif user['Item']['Password'] != password:
        message = "Incorrect password. Account not deleted."
    else:
        user_table.delete_item(Key={'Name': username})
        message = "Your account has been deleted."

    return render_template('dynamo.html', message=message)

# ------------------------------------------
# Run the Flask app
# ------------------------------------------
if __name__ == '__main__':
    # Run on all interfaces with debug mode enabled
    app.run(host='0.0.0.0', port=8080, debug=True)
