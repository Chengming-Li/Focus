import os
import psycopg2
from dotenv import load_dotenv
from flask import request, jsonify
from datetime import datetime

# region SQL commands
# when adding new settings, edit to CREATE_USERS_TABLE, INSERT_USER, EDIT_SETTINGS, editSettings(), and getUser()
CREATE_USERS_TABLE = "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, email TEXT, timezone TEXT);"
INSERT_USER = "INSERT INTO users (username, email, timezone) VALUES (%s, %s, %s) RETURNING id;"
FETCH_USER_INFO = "SELECT username, email, timezone FROM users WHERE id = (%s);"
DELETE_USER = "DELETE FROM users WHERE id = (%s);"
CREATE_INTERVALS_TABLE = "CREATE TABLE IF NOT EXISTS intervals (interval_id SERIAL PRIMARY KEY, user_id INT, project_id INT, name TEXT, start_time timestamptz, end_time timestamptz, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);" # FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
START_INTERVAL = "INSERT INTO intervals (user_id, project_id, name, start_time) VALUES (%s, %s, %s, %s) RETURNING interval_id;"
END_INTERVAL = "UPDATE intervals SET end_time = (%s) WHERE interval_id = (%s);"
EDIT_INTERVAL = "UPDATE intervals SET name = (%s), project_id = (%s), start_time = (%s), end_time = (%s) WHERE interval_id = (%s);"
GET_ALL_INACTIVE_INTERVALS_BY_USER = "SELECT * FROM intervals WHERE user_id = %s AND end_time IS NOT NULL ORDER BY start_time;"
GET_ALL_ACTIVE_INTERVALS_BY_USER = "SELECT * FROM intervals WHERE user_id = %s AND end_time IS NULL ORDER BY start_time;"
DELETE_INTERVAL = "DELETE FROM intervals WHERE interval_id = (%s);"
EDIT_SETTINGS = "UPDATE users SET timezone = (%s) WHERE id = (%s) RETURNING id;"
# endregion

# loads environment variables from .env and other miscellaneous stuff
load_dotenv()
url = os.getenv("DATABASE_URL")

def establishConnection():
    """
    Establishes connection with Postgres database

    @returns {connection}
    """
    return psycopg2.connect(url)

# API Functions
# region general functions, for testing
def getTable(tableName):
    """
    Fetches entire table from database

    @param {int} tableName: the name of the table

    @returns {json}: a list of dictionaries corresponding to the rows, each dictionary's keys corresponds to the columns
    """
    connection = establishConnection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {tableName}",)
                table = cursor.fetchall()
                result = [dict(zip([column[0] for column in cursor.description], row)) for row in table]
    except Exception as e:
        return {"error": f"Failed to get table: {str(e)}"}, 500
    return jsonify(result)

def deleteTable(tableName):
    """
    Deletes entire table from database

    @param {int} tableName: the name of the table

    @returns {json}: a dictionary containing key "name" with the name of the deleted table
    """
    connection = establishConnection()
    data = request.get_json()
    if data["confimration"] != "Confirm":
        return {"error": "Access Denied"}, 403
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE {tableName}",)
                result = [{"name": tableName}]
    except Exception as e:
        return {"error": f"Failed to delete Table: {str(e)}"}, 500
    return jsonify(result)

# endregion

# region user functions
def getUser(userId):
    """
    Fetch user information from database

    @param {int} userId: the ID of the user

    @returns {json}: a dictionary with the keys "userInfo", "intervals", and "activeInterval"
        "userInfo" points to a dict with keys "email", "id", "timezone", and "username"
        "intervals" points to a list of dictionaries, each with the keys "end_time", "start_time", "interval_id", "name", "project_id", and "user_id"
        "activeInterval" points to the current interval that hasn't been ended, with the keys "end_time", "start_time", "interval_id", "name", "project_id", and "user_id"
    """
    connection = establishConnection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(FETCH_USER_INFO, (userId,))
                data = cursor.fetchone()
                user = {"id": userId, "username" : data[0], "email" : data[1], "timezone" : data[2]}
                cursor.execute(GET_ALL_INACTIVE_INTERVALS_BY_USER, (userId,))
                data = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

                for item in data:
                    startTime = item['start_time']
                    item['start_time'] = startTime.strftime('%A %d %B %Y %H:%M:%S %Z') if startTime else None
                    endTime = item['end_time']
                    item['end_time'] = endTime.strftime('%A %d %B %Y %H:%M:%S %Z') if endTime else None

                cursor.execute(GET_ALL_ACTIVE_INTERVALS_BY_USER, (userId,))
                active = dict(zip([column[0] for column in cursor.description], cursor.fetchone()))
    except Exception as e:
        return {"error": f"Failed to get user: {str(e)}"}, 500
    return jsonify({"userInfo" : user, "intervals" : data, "activeInterval" : active})

def createUser():
    """
    Create a new user in table users and return their ID
    Json Body:
        "username" : (str) name of user
        "email" : (str) email of user
        "timezone" : (str) abbreviated timezone of user

    @returns {json}: a dictionary containing the key "id", with user's ID
    """
    connection = establishConnection()
    data = request.get_json()
    username = data["username"]
    email = data["email"]
    timezone = data["timezone"]
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_USERS_TABLE)
                connection.commit()
                cursor.execute(INSERT_USER, (username, email, timezone,))
                userId = cursor.fetchone()[0]
    except Exception as e:
        return {"error": f"Failed to create user: {str(e)}"}, 500
    return jsonify({"id": userId}), 201

def deleteUser(userId):
    """
    Delete user from database

    @param {int} userId: the ID of the user

    @returns {json}: a dictionary containing the key "id" with the user's ID
    """
    connection = establishConnection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(DELETE_USER, (userId,))
                result = [{"id": userId}]
    except Exception as e:
        return {"error": f"Failed to delete user: {str(e)}"}, 500
    return jsonify(result)

def editSettings(userId):
    """
    Changes the settings associated with an account
    Json Body:
        "timezone" : (str) abbreviated timezone of user

    @returns {json}: a dictionary containing the key "id", with user's ID, and "timezone", with the new timezone
    """
    connection = establishConnection()
    data = request.get_json()
    timezone = data["timezone"]
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(EDIT_SETTINGS, (timezone, userId,))
                userId = cursor.fetchone()[0]
    except Exception as e:
        return {"error": f"Failed to edit settings: {str(e)}"}, 500
    return jsonify({"id": userId, "timezone" : timezone}), 201
# endregion

# region interval functions
def startInterval():
    """
    Create a new interval and return its ID
    Json Body:
        "name" : (str) name of the interval
        "user_id" : (int) ID of the user creating the interval
        "project_id" : (int) ID of the user creating the interval

    @returns {json}: a dictionary containing the key "id", with interval ID
    """
    connection = establishConnection()
    data = request.get_json()
    name = data["name"]
    userID = data["user_id"]
    projectID = data["project_id"]
    startTime = datetime.now()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_INTERVALS_TABLE)
                connection.commit()
                cursor.execute(START_INTERVAL, (userID, projectID, name, startTime,))
                intervalID = cursor.fetchone()[0]
    except Exception as e:
        return {"error": f"Failed to start the interval: {str(e)}"}, 500
    return jsonify({"id": intervalID}), 201

def endInterval(intervalId):
    """
    Ends interval with ID
    
    @param {int} intervalId: the ID of the interval

    @returns {json}: a dictionary containing the key "id", with interval ID, and "endTime", with string representation of end time
    """
    connection = establishConnection()
    endTime = datetime.now()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(END_INTERVAL, (endTime, intervalId,))
    except Exception as e:
        return {"error": f"Failed to end interval: {str(e)}"}, 500
    return jsonify({"id": intervalId, "endTime" : endTime}), 201

def editInterval(intervalId):
    """
    Edits interval with ID
    Json Body:
        "name" : (str) name of the interval
        "project_id" : (int) ID of the user creating the interval
        "start_time" : (str) String representing a timestamp in YYYY-MM-DD HH:MI:SS fomat
        "end_time" : (str) String representing a timestamp in YYYY-MM-DD HH:MI:SS fomat
    
    @param {int} intervalId: the ID of the interval

    @returns {json}: a dictionary containing the key "id", with interval ID
    """
    connection = establishConnection()
    data = request.get_json()
    name = data["name"]
    projectID = data["project_id"]
    startTime = data["start_time"]
    endTime = data["end_time"]
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(EDIT_INTERVAL, (name, projectID, startTime, endTime, intervalId,))
    except Exception as e:
        return {"error": f"Failed to edit interval: {str(e)}"}, 500
    return jsonify({"id": intervalId}), 201

def deleteInterval(intervalId):
    """
    Delete interval from database

    @param {int} intervalId: the ID of the interval

    @returns {json}: a dictionary containing the key "id" with the user's ID
    """
    connection = establishConnection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(DELETE_INTERVAL, (intervalId,))
                result = [{"id": intervalId}]
    except Exception as e:
        return {"error": f"Failed to delete interval: {str(e)}"}, 500
    return jsonify(result)
# endregion