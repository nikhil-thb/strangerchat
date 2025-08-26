from flask import Flask, render_template, request, session
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
age_verified_users = set()
privacy_accepted_users = set()

def check_message(message):
    """Check if message contains NSFW content"""
    return profanity.contains_profanity(message)

def get_current_time():
    """Get formatted current time"""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

@app.route('/')
def index():
    return render_template('chat.html', 
                         current_time=get_current_time(),
                         current_user="nikhil-thb")

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        session_id = request.sid
        active_users[session_id] = None
        emit('connected', {
            'user_id': session_id,
            'timestamp': get_current_time()
        })
    except Exception as e:
        print(f"Connection error: {str(e)}")

@socketio.on('verify_age')
def handle_age_verification(data):
    """Handle age verification"""
    try:
        user_sid = request.sid
        if data.get('isAdult'):
            age_verified_users.add(user_sid)
            emit('age_verified', {
                'timestamp': get_current_time()
            })
    except Exception as e:
        print(f"Age verification error: {str(e)}")

@socketio.on('accept_privacy')
def handle_privacy_acceptance():
    """Handle privacy policy acceptance"""
    try:
        user_sid = request.sid
        privacy_accepted_users.add(user_sid)
        emit('privacy_accepted', {
            'timestamp': get_current_time()
        })
    except Exception as e:
        print(f"Privacy acceptance error: {str(e)}")

@socketio.on('find_stranger')
def handle_find_stranger():
    """Handle finding a chat partner"""
    try:
        user_sid = request.sid
        
        # Verify age and privacy policy acceptance
        if user_sid not in age_verified_users:
            emit('error', {
                'message': 'Age verification required',
                'timestamp': get_current_time()
            })
            return
            
        if user_sid not in privacy_accepted_users:
            emit('error', {
                'message': 'Privacy policy acceptance required',
                'timestamp': get_current_time()
            })
            return
        
        # Leave current room if any
        if active_users.get(user_sid):
            leave_room(active_users[user_sid])
            active_users[user_sid] = None
        
        # Check if user is banned
        if user_sid in banned_users:
            if datetime.utcnow() < banned_users[user_sid]:
                remaining = (banned_users[user_sid] - datetime.utcnow()).seconds // 60
                emit('banned', {
                    'message': 'You are banned for sending inappropriate content.',
                    'duration': remaining,
                    'timestamp': get_current_time()
                })
                return
            else:
                del banned_users[user_sid]
        
        emit('searching', {
            'message': 'Looking for a stranger...',
            'timestamp': get_current_time()
        })
        
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
                    'message': 'You are now chatting with a stranger!',
                    'timestamp': get_current_time()
                }, room=room)
                return
        
        # No partner found
        emit('searching', {
            'message': 'Waiting for someone to join...',
            'timestamp': get_current_time()
        })
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
            if datetime.utcnow() < banned_users[user_sid]:
                remaining = (banned_users[user_sid] - datetime.utcnow()).seconds // 60
                emit('banned', {
                    'message': 'You are banned for sending inappropriate content.',
                    'duration': remaining,
                    'timestamp': get_current_time()
                })
                return
            else:
                del banned_users[user_sid]

        # Check for NSFW content
        if check_message(message):
            # Ban user for 1 hour
            banned_users[user_sid] = datetime.utcnow() + timedelta(hours=1)
            emit('banned', {
                'message': 'You are banned for sending inappropriate content.',
                'duration': 60,
                'timestamp': get_current_time()
            })
            return

        if room:
            emit('message', {
                'message': message,
                'type': 'stranger',
                'timestamp': get_current_time()
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
                'message': 'Stranger has disconnected.',
                'timestamp': get_current_time()
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
                    'message': 'Stranger has disconnected.',
                    'timestamp': get_current_time()
                }, room=room)
            del active_users[user_sid]
        
        # Clean up verification records
        if user_sid in age_verified_users:
            age_verified_users.remove(user_sid)
        if user_sid in privacy_accepted_users:
            privacy_accepted_users.remove(user_sid)
            
    except Exception as e:
        print(f"Disconnect error: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, debug=True)