from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from better_profanity import profanity
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app)

# Store active users and their rooms
active_users = {}
banned_users = {}
user_rooms = {}

def check_message(message):
    """Check if message contains NSFW content"""
    return profanity.contains_profanity(message)

@app.route('/')
def index():
    return render_template('chat.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        session_id = request.sid
        active_users[session_id] = None  # No room assigned yet
        emit('connected', {'user_id': session_id})
    except Exception as e:
        print(f"Connection error: {str(e)}")

@socketio.on('find_stranger')
def handle_find_stranger():
    """Handle finding a chat partner"""
    try:
        user_sid = request.sid
        
        # Leave current room if any
        if active_users.get(user_sid):
            leave_room(active_users[user_sid])
            active_users[user_sid] = None
        
        # Check if user is banned
        if user_sid in banned_users:
            if datetime.now() < banned_users[user_sid]:
                remaining = (banned_users[user_sid] - datetime.now()).seconds // 60
                emit('banned', {
                    'message': 'You are banned for sending inappropriate content.',
                    'duration': remaining
                })
                return
            else:
                del banned_users[user_sid]
        
        emit('searching', {'message': 'Looking for a stranger...'})
        
        # Find available partner
        for potential_partner in active_users:
            if (potential_partner != user_sid and 
                not active_users[potential_partner]):
                # Create new room
                room = secrets.token_hex(8)
                active_users[user_sid] = room
                active_users[potential_partner] = room
                
                # Join both users to room
                join_room(room)
                join_room(room, sid=potential_partner)
                
                # Notify both users
                emit('paired', {
                    'message': 'You are now chatting with a stranger!'
                }, room=room)
                return
        
        # No partner found
        emit('searching', {'message': 'Waiting for someone to join...'})
    except Exception as e:
        print(f"Find stranger error: {str(e)}")

@socketio.on('message')
def handle_message(data):
    """Handle chat messages"""
    try:
        user_sid = request.sid
        message = data.get('message', '').strip()
        room = active_users.get(user_sid)

        # Check if user is banned
        if user_sid in banned_users:
            if datetime.now() < banned_users[user_sid]:
                remaining = (banned_users[user_sid] - datetime.now()).seconds // 60
                emit('banned', {
                    'message': 'You are banned for sending inappropriate content.',
                    'duration': remaining
                })
                return
            else:
                del banned_users[user_sid]

        # Check for NSFW content
        if check_message(message):
            # Ban user for 1 hour
            banned_users[user_sid] = datetime.now() + timedelta(hours=1)
            emit('banned', {
                'message': 'You are banned for sending inappropriate content.',
                'duration': 60
            })
            return

        if room:
            emit('message', {
                'message': message,
                'type': 'stranger'
            }, room=room, include_self=False)
    except Exception as e:
        print(f"Message error: {str(e)}")

@socketio.on('disconnect_chat')
def handle_disconnect_chat():
    """Handle manual chat disconnection"""
    try:
        user_sid = request.sid
        room = active_users.get(user_sid)
        
        if room:
            leave_room(room)
            emit('partner_disconnected', {
                'message': 'Stranger has disconnected.'
            }, room=room)
            active_users[user_sid] = None
    except Exception as e:
        print(f"Disconnect chat error: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        user_sid = request.sid
        if user_sid in active_users:
            room = active_users[user_sid]
            if room:
                leave_room(room)
                emit('partner_disconnected', {
                    'message': 'Stranger has disconnected.'
                }, room=room)
            del active_users[user_sid]
    except Exception as e:
        print(f"Disconnect error: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, debug=True)