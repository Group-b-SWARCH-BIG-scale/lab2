import os
import textwrap


def generate_database(name):
    path = f'skeleton/{name}'
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, 'init.sql'), 'w') as f:
        f.write(textwrap.dedent("""
            CREATE TABLE IF NOT EXISTS systems (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255)
            );
        """))


def generate_backend(name, database=None, nosql_database=None):
    path = f'skeleton/{name}'
    os.makedirs(path, exist_ok=True)

    with open(os.path.join(path, 'app.py'), 'w') as f:
        f.write(textwrap.dedent(f"""
            from flask import Flask, request, jsonify
            import mysql.connector
            import boto3
            import os

            app = Flask(__name__)

            MYSQL_HOST = '{database}' if '{database}' else None
            DYNAMO_HOST = 'http://{nosql_database}:8000' if '{nosql_database}' else None

            @app.route('/create', methods=['POST'])
            def create():
                data = request.json
                results = {{}}

                # --- SQL Insert ---
                if MYSQL_HOST:
                    conn = mysql.connector.connect(
                        host=MYSQL_HOST,
                        user='root',
                        password='root',
                        database='{database}'
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
                    table.put_item(Item={{'id': str(hash(data['name'])), 'name': data['name']}})
                    results['dynamo'] = 'created'

                return jsonify(results)

            @app.route('/systems')
            def get_systems():
                result = {{}}

                if MYSQL_HOST:
                    conn = mysql.connector.connect(
                        host=MYSQL_HOST,
                        user='root',
                        password='root',
                        database='{database}'
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
        """))

    with open(os.path.join(path, 'Dockerfile'), 'w') as f:
        f.write(textwrap.dedent("""
            FROM python:3.11-slim
            WORKDIR /app
            COPY . .
            RUN pip install flask mysql-connector-python boto3
            CMD ["python", "app.py"]
        """))

def generate_frontend(name, backend):
    path = f'skeleton/{name}'
    os.makedirs(path, exist_ok=True)

    with open(os.path.join(path, 'package.json'), 'w') as f:
        f.write(textwrap.dedent("""
            {
                "name": "frontend",
                "version": "1.0.0",
                "main": "app.js",
                "dependencies": {
                    "express": "^4.18.2",
                    "axios": "^1.6.7"
                }
            }
        """))

    with open(os.path.join(path, 'Dockerfile'), 'w') as f:
        f.write(textwrap.dedent("""
            FROM node:18
            WORKDIR /app
            COPY . .
            RUN npm install
            CMD ["node", "app.js"]
        """))

    with open(os.path.join(path, 'app.js'), 'w') as f:
        f.write(textwrap.dedent(f"""
            const express = require('express');
            const axios = require('axios');
            const app = express();

            app.use(express.json());
            app.use(express.urlencoded({{ extended: true }}));

            const BACKEND_URL = 'http://{backend}:80';

            app.get('/', async (req, res) => {{
                try {{
                    const response = await axios.get(`${{BACKEND_URL}}/systems`);
                    const systems = response.data.systems;
                    let list = systems.map(([id, name]) => `<li>${{name}}</li>`).join('');
                    res.send(`
                        <html>
                            <body>
                                <h1>Frontend</h1>
                                <form method="POST" action="/create">
                                    <input name="name" />
                                    <button type="submit">Create</button>
                                </form>
                                <ul>${{list}}</ul>
                            </body>
                        </html>
                    `);
                }} catch (err) {{
                    res.status(500).send("Error contacting backend");
                }}
            }});

            app.post('/create', async (req, res) => {{
                const name = req.body.name;
                await axios.post(`${{BACKEND_URL}}/create`, {{ name }});
                res.redirect('/');
            }});

            app.listen(80, () => console.log("Frontend running on port 80"));
        """))

def generate_nosql_database(name):
    path = f'skeleton/{name}'
    os.makedirs(path, exist_ok=True)

    # DynamoDB Local no necesita archivos de inicialización SQL,
    # pero creamos un README explicativo
    with open(os.path.join(path, 'README.md'), 'w') as f:
        f.write(textwrap.dedent(f"""
            # {name} - DynamoDB Local
            Este servicio ejecuta una instancia local de DynamoDB.

            Accesible en puerto 8000.
        """))

def generate_docker_compose(components):
    path = 'skeleton/'
    os.makedirs(path, exist_ok=True)

    with open(os.path.join(path, 'docker-compose.yml'), 'w') as f:
        sorted_components = dict(sorted(components.items(), key=lambda item: 0 if item[1] in ("database", "nosql") else 1))
        f.write("version: '3.9'\nservices:\n")

        db = None
        nosql_db = None

        for i, (name, ctype) in enumerate(sorted_components.items()):
            port = 8000 + i
            f.write(f"  {name}:\n")

            if ctype == "database":
                db = name
                f.write("    image: mysql:8\n")
                f.write("    environment:\n")
                f.write("      - MYSQL_ROOT_PASSWORD=root\n")
                f.write(f"      - MYSQL_DATABASE={name}\n")
                f.write("    volumes:\n")
                f.write(f"      - ./{name}/init.sql:/docker-entrypoint-initdb.d/init.sql\n")
                f.write("    ports:\n")
                f.write("      - '3306:3306'\n")

            elif ctype == "nosql":
                nosql_db = name
                f.write("    image: amazon/dynamodb-local:latest\n")
                f.write("    command: '-jar DynamoDBLocal.jar -sharedDb'\n")
                f.write("    ports:\n")
                f.write("      - '8000:8000'\n")
                f.write("    volumes:\n")
                f.write(f"      - ./{name}:/data\n")

            else:
                f.write(f"    build: ./{name}\n")
                f.write(f"    ports:\n")
                f.write(f"      - '{port}:80'\n")
                if ctype == "backend":
                    f.write(f"    depends_on:\n")
                    if db:
                        f.write(f"      - {db}\n")
                    if nosql_db:
                        f.write(f"      - {nosql_db}\n")

        f.write("\nnetworks:\n  default:\n    driver: bridge\n")


def apply_transformations(model):
    components = {}
    backend_name = None
    database_name = None
    nosql_name = None

    for e in model.elements:
        if e.__class__.__name__ == 'Component':
            components[e.name] = e.type
            if e.type == 'backend':
                backend_name = e.name
            elif e.type == 'database':
                database_name = e.name
            elif e.type == 'nosql':
                nosql_name = e.name

    for name, ctype in components.items():
        if ctype == 'database':
            generate_database(name)
        elif ctype == 'nosql':
            generate_nosql_database(name)
        elif ctype == 'backend':
            generate_backend(name, database=database_name, nosql_database=nosql_name)
        elif ctype == 'frontend':
            generate_frontend(name, backend=backend_name)

    generate_docker_compose(components)
  