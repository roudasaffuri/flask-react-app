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

        # Return token AND email here!
        return jsonify({'token': token, 'email': username}), 200

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
  { "id": 1, "title": "My First Post", "paragraph": "This is the content" },
  { "id": 2, "title": "Another Post", "paragraph": "More content here" }
]

    return jsonify(posts_data), 200




@app.route('/notes', methods=['GET'])
def get_notes():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_id = user[0]

        cursor.execute("SELECT id, title, content, created_at FROM notes WHERE user_id=%s", (user_id,))
        rows = cursor.fetchall()

        notes = []
        for row in rows:
            created_at = row[3]
            # If created_at is a string, convert to datetime
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    # fallback or leave as string
                    created_at = None

            notes.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": created_at.isoformat() if created_at else None
            })

        return jsonify(notes), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/notes', methods=['POST'])
def add_note():
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    email = data.get('email')

    if not title or not content or not email:
        return jsonify({'error': 'Title, content, and email are required'}), 400

    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Get user id by email
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_id = user[0]

        # Insert the new note

        cursor.execute(
            "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s) RETURNING id",
            (user_id, title, content)
        )
        note_id = cursor.fetchone()[0]
        conn.commit()

        # Return the newly created note as JSON
        return jsonify({
            "id": note_id,
            "title": title,
            "content": content
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    # Optional: get user email or token from request headers if you want to verify ownership

    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Check if the note exists
        cursor.execute("SELECT id FROM notes WHERE id=%s", (note_id,))
        note = cursor.fetchone()
        if not note:
            return jsonify({'error': 'Note not found'}), 404

        # Delete the note
        cursor.execute("DELETE FROM notes WHERE id=%s", (note_id,))
        conn.commit()

        return jsonify({'message': f'Note {note_id} deleted successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
