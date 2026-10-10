from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and rooms
users = {}
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    users[user_id] = {'name': None, 'room': None}
    print(f'Client {user_id} connected')
    emit('connect_response', {'data': 'Connected to server', 'user_id': user_id})

@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if user_id in users:
        room = users[user_id].get('room')
        if room:
            leave_room(room)
            emit('user_left', {
                'message': f"{users[user_id]['name']} left the chat",
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }, room=room)
        del users[user_id]
    print(f'Client {user_id} disconnected')

@socketio.on('join')
def on_join(data):
    user_id = session.get('user_id')
    username = data['username']
    room = data['room']
    
    if user_id not in users:
        return
    
    users[user_id]['name'] = username
    users[user_id]['room'] = room
    join_room(room)
    
    if room not in rooms:
        rooms[room] = []
    rooms[room].append({'user_id': user_id, 'name': username})
    
    emit('user_joined', {
        'message': f"{username} joined the chat",
        'users': len(rooms.get(room, [])),
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=room)

@socketio.on('message')
def handle_message(data):
    user_id = session.get('user_id')
    if user_id not in users:
        return
    
    room = users[user_id].get('room')
    username = users[user_id].get('name')
    message = data.get('message', '')
    
    if message.strip() and room:
        emit('new_message', {
            'username': username,
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }, room=room)

@socketio.on('get_users')
def get_users():
    user_id = session.get('user_id')
    if user_id not in users:
        return
    
    room = users[user_id].get('room')
    room_users = rooms.get(room, [])
    
    emit('users_list', {
        'users': [u['name'] for u in room_users]
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
