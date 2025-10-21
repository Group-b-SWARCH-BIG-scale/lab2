
from flask import Flask, request, jsonify
import mysql.connector
import boto3
import os

app = Flask(__name__)

MYSQL_HOST = 'lssa_db' if 'lssa_db' else None
DYNAMO_HOST = 'http://lssa_db_nosql:8000' if 'lssa_db_nosql' else None

@app.route('/create', methods=['POST'])
def create():
    data = request.json
    results = {}

    # --- SQL Insert ---
    if MYSQL_HOST:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user='root',
            password='root',
            database='lssa_db'
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO systems (name) VALUES (%s)", (data['name'],))
        conn.commit()
        cursor.close()
        conn.close()
        results['mysql'] = 'created'

    # --- DynamoDB Insert ---
    if DYNAMO_HOST:
        dynamodb = boto3.resource('dynamodb', endpoint_url=DYNAMO_HOST, region_name='us-west-2')
        table = dynamodb.Table('Systems')
        table.put_item(Item={'id': str(hash(data['name'])), 'name': data['name']})
        results['dynamo'] = 'created'

    return jsonify(results)

@app.route('/systems')
def get_systems():
    result = {}

    if MYSQL_HOST:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user='root',
            password='root',
            database='lssa_db'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM systems")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        result['mysql'] = rows

    if DYNAMO_HOST:
        dynamodb = boto3.resource('dynamodb', endpoint_url=DYNAMO_HOST, region_name='us-west-2')
        table = dynamodb.Table('Systems')
        items = table.scan()['Items']
        result['dynamo'] = items

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
