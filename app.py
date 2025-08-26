from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and chat pairs
active_users = {}  # {user_id: {'socket_id': sid, 'partner': partner_id, 'room': room_id}}
waiting_queue = []  # List of user_ids waiting for a partner

def create_room_id():
    """Generate a unique room ID for chat pairs"""
    return str(uuid.uuid4())

def pair_users():
    """Pair two users from the waiting queue"""
    if len(waiting_queue) >= 2:
        user1_id = waiting_queue.pop(0)
        user2_id = waiting_queue.pop(0)
        
        # Create a room for the pair
        room_id = create_room_id()
        
        # Update user data
        active_users[user1_id]['partner'] = user2_id
        active_users[user1_id]['room'] = room_id
        active_users[user2_id]['partner'] = user1_id
        active_users[user2_id]['room'] = room_id
        
        # Join both users to the room
        socketio.emit('paired', {
            'room': room_id,
            'message': 'You are now connected to a stranger!'
        }, room=active_users[user1_id]['socket_id'])
        
        socketio.emit('paired', {
            'room': room_id,
            'message': 'You are now connected to a stranger!'
        }, room=active_users[user2_id]['socket_id'])

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'User connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'User disconnected: {request.sid}')
    
    # Find and remove user from active users
    user_to_remove = None
    for user_id, user_data in active_users.items():
        if user_data['socket_id'] == request.sid:
            user_to_remove = user_id
            break
    
    if user_to_remove:
        # If user has a partner, notify them
        user_data = active_users[user_to_remove]
        if 'partner' in user_data and user_data['partner']:
            partner_id = user_data['partner']
            if partner_id in active_users:
                socketio.emit('partner_disconnected', {
                    'message': 'Stranger has disconnected.'
                }, room=active_users[partner_id]['socket_id'])
                
                # Reset partner's data
                active_users[partner_id]['partner'] = None
                active_users[partner_id]['room'] = None
        
        # Remove from waiting queue if present
        if user_to_remove in waiting_queue:
            waiting_queue.remove(user_to_remove)
        
        # Remove from active users
        del active_users[user_to_remove]

@socketio.on('find_stranger')
def handle_find_stranger():
    user_id = str(uuid.uuid4())
    
    # Add user to active users
    active_users[user_id] = {
        'socket_id': request.sid,
        'partner': None,
        'room': None
    }
    
    # Add to waiting queue
    waiting_queue.append(user_id)
    
    emit('searching', {'message': 'Looking for a stranger...'})
    
    # Try to pair users
    pair_users()

@socketio.on('send_message')
def handle_message(data):
    message = data.get('message', '').strip()
    if not message:
        return
    
    # Find the user
    user_id = None
    for uid, user_data in active_users.items():
        if user_data['socket_id'] == request.sid:
            user_id = uid
            break
    
    if user_id and active_users[user_id]['partner']:
        partner_id = active_users[user_id]['partner']
        room_id = active_users[user_id]['room']
        
        # Send message to partner
        if partner_id in active_users:
            socketio.emit('receive_message', {
                'message': message,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'sender': 'stranger'
            }, room=active_users[partner_id]['socket_id'])
            
            # Echo back to sender
            emit('receive_message', {
                'message': message,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'sender': 'you'
            })

@socketio.on('disconnect_chat')
def handle_disconnect_chat():
    # Find the user
    user_id = None
    for uid, user_data in active_users.items():
        if user_data['socket_id'] == request.sid:
            user_id = uid
            break
    
    if user_id and active_users[user_id]['partner']:
        partner_id = active_users[user_id]['partner']
        
        # Notify partner
        if partner_id in active_users:
            socketio.emit('partner_disconnected', {
                'message': 'Stranger has disconnected.'
            }, room=active_users[partner_id]['socket_id'])
            
            # Reset partner's data
            active_users[partner_id]['partner'] = None
            active_users[partner_id]['room'] = None
        
        # Reset user's data
        active_users[user_id]['partner'] = None
        active_users[user_id]['room'] = None
        
        emit('chat_ended', {'message': 'You have disconnected from the chat.'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)