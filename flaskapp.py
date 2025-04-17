from flask import Flask, render_template, request, redirect, url_for
import pymysql
import creds
from dbCode import *
import boto3

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
user_table = dynamodb.Table('Countries')

app = Flask(__name__)

# SQL query function (exclude GNPOld, SurfaceArea, LocalName)
def get_filtered_countries(country_name=None):
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

@app.route('/', methods=['GET', 'POST'])
def auth():
    message = ""
    if request.method == 'POST':
        action = request.form['action']
        username = request.form['username']
        password = request.form['password']

        if action == 'signup':
            existing_user = user_table.get_item(Key={'Name': username})
            if 'Item' in existing_user:
                message = "Username already exists. Please choose another."
            else:
                user_table.put_item(Item={'Name': username, 'Password': password})
                message = "Signup successful! You can now log in."

        elif action == 'login':
            user = user_table.get_item(Key={'Name': username})
            if 'Item' in user and user['Item']['Password'] == password:
                return redirect(url_for('sql'))
            else:
                message = "Invalid username or password."

    return render_template('dynamo.html', message=message)

@app.route('/sql', methods=['GET', 'POST'])
def sql():
    message = ""
    results = []

    if request.method == 'POST':
        action = request.form['action']
        if action == 'search':
            country_name = request.form['country']
            results = get_filtered_countries(country_name)
            if not results:
                message = f"No results found for '{country_name}'."
        elif action == 'reset':
            results = get_filtered_countries()
    else:
        results = get_filtered_countries()

    return render_template('index.html', results=results, message=message)

@app.route('/update-password', methods=['GET', 'POST'])
def update_password():
    message = ""
    if request.method == 'POST':
        username = request.form['username']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        response = user_table.get_item(Key={'Name': username})
        if 'Item' not in response:
            message = "User not found."
        elif response['Item']['Password'] != old_password:
            message = "Old password is incorrect."
        else:
            user_table.update_item(
                Key={'Name': username},
                UpdateExpression='SET Password = :newpw',
                ExpressionAttributeValues={':newpw': new_password}
            )
            message = "Password updated successfully!"

    return render_template('update_password.html', message=message)

@app.route('/delete-account', methods=['POST'])
def delete_account():
    username = request.form['username']
    password = request.form['password']

    user = user_table.get_item(Key={'Name': username})
    if 'Item' not in user:
        message = "User not found."
    elif user['Item']['Password'] != password:
        message = "Incorrect password. Account not deleted."
    else:
        user_table.delete_item(Key={'Name': username})
        message = "Your account has been deleted."

    return render_template('dynamo.html', message=message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
