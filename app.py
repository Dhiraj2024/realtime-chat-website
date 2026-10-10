from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

# Configure SocketIO for better concurrent connections
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

# Store active users and rooms data
users = {}
rooms_data = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    users[user_id] = {'name': None, 'room': None}
    print(f'✅ Client {user_id} connected')
    print(f'📊 Total users connected: {len(users)}')
    emit('connect_response', {
        'data': 'Connected to server',
        'user_id': user_id,
        'status': 'success'
    })

@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if user_id and user_id in users:
        room = users[user_id].get('room')
        username = users[user_id].get('name')
        
        if room and username:
            # Notify others in room that user left
            emit('user_left', {
                'message': f"🚪 {username} left the chat",
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }, room=room)
            
            # Remove from room users list
            if room in rooms_data:
                rooms_data[room] = [u for u in rooms_data[room] if u['user_id'] != user_id]
                if not rooms_data[room]:
                    del rooms_data[room]
            
            print(f"❌ User '{username}' left room '{room}'")
        
        del users[user_id]
        print(f'❌ Client {user_id} disconnected')
        print(f'📊 Total users connected: {len(users)}')

@socketio.on('join')
def on_join(data):
    user_id = session.get('user_id')
    username = data.get('username', '').strip()
    room = data.get('room', '').strip()
    
    # Validate input
    if not username or not room:
        emit('error', {'message': 'Username and room are required'})
        return
    
    if user_id not in users:
        emit('error', {'message': 'User not found. Reconnect and try again.'})
        return
    
    # Update user data
    users[user_id]['name'] = username
    users[user_id]['room'] = room
    
    # Join the room
    join_room(room)
    print(f"✅ User '{username}' (ID: {user_id}) joined room '{room}'")
    
    # Initialize room if not exists
    if room not in rooms_data:
        rooms_data[room] = []
    
    # Add user to room
    rooms_data[room].append({'user_id': user_id, 'name': username})
    
    # Notify all users in room
    user_count = len(rooms_data.get(room, []))
    print(f"📊 Room '{room}' now has {user_count} user(s)")
    
    emit('user_joined', {
        'message': f"👋 {username} joined the chat",
        'users': user_count,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=room)
    
    # Send updated users list
    emit('users_list', {
        'users': [u['name'] for u in rooms_data.get(room, [])]
    }, room=room)

@socketio.on('message')
def handle_message(data):
    user_id = session.get('user_id')
    
    if user_id not in users:
        emit('error', {'message': 'User session expired'})
        return
    
    room = users[user_id].get('room')
    username = users[user_id].get('name')
    message = data.get('message', '').strip()
    
    # Validate message
    if not message or not room:
        return
    
    print(f"💬 Message from {username} in {room}: {message}")
    
    # Broadcast to room
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
    room_users = rooms_data.get(room, [])
    
    emit('users_list', {
        'users': [u['name'] for u in room_users]
    })

if __name__ == '__main__':
    print("🚀 Starting Real-Time Chat Server...")
    print("📍 Visit http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
