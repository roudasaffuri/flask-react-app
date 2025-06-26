# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from psycopg2 import sql
from backend.database import create_connection  # Your DB connection helper
import jwt
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret in production

CORS(app, supports_credentials=True)

# Protected route example (home page)
@app.route('/')
def index():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Authorization header missing'}), 401

    try:
        token = auth_header.split(" ")[1]
        decoded = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return jsonify({'message': 'Welcome to the Flask backend!', 'email': decoded['email']})
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

# Login - returns JWT
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('email')
    password = data.get('password')

    connection = create_connection()
    cursor = connection.cursor()
    try:
        query = sql.SQL("SELECT * FROM users WHERE email=%s")
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        stored_password = user[4]
        if password != stored_password:
            return jsonify({'error': 'Invalid password'}), 401

        payload = {
            'email': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, app.secret_key, algorithm='HS256')
        return jsonify({'token': token}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': 'Server error'}), 500

    finally:
        cursor.close()
        connection.close()

# Signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    email = data.get('email')
    password = data.get('password')

    connection = create_connection()
    cursor = connection.cursor()

    try:
        insert_query = sql.SQL(
            "INSERT INTO users (firstname, lastname, email, password) VALUES (%s, %s, %s, %s)"
        )
        cursor.execute(insert_query, (firstname, lastname, email, password))
        connection.commit()
        return jsonify({"message": "User created successfully!"}), 201

    except Exception as e:
        print("Signup Error:", e)
        return jsonify({"error": "User not successful!"}), 401

    finally:
        cursor.close()
        connection.close()

@app.route('/posts', methods=['GET'])
def posts():
    posts_data = [
        {"id": 1, "paragraph": "This is the first post."},
        {"id": 2, "paragraph": "This is the second post."},
        {"id": 3, "paragraph": "Here's another post."},
    ]

    return jsonify(posts_data), 200




if __name__ == '__main__':
    app.run(debug=True)
