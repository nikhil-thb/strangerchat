const socket = io();
let currentRoom = null;
let userId = null;

// Connect to socket
socket.on('connect', () => {
    console.log('Connected to server');
    findNewPartner();
});

socket.on('connected', (data) => {
    userId = data.user_id;
});

// Handle finding partner
function findNewPartner() {
    socket.emit('find_partner');
    displaySystemMessage('Looking for a partner...');
}

// Handle chat started
socket.on('chat_started', (data) => {
    currentRoom = data.room;
    displaySystemMessage('Connected with a stranger! Say hi!');
});

// Handle waiting for partner
socket.on('waiting_for_partner', () => {
    displaySystemMessage('Waiting for a partner...');
});

// Handle messages
socket.on('message', (data) => {
    const isOwnMessage = data.user_id === userId;
    displayMessage(data.message, isOwnMessage, data.timestamp);
});

// Handle partner disconnection
socket.on('partner_disconnected', () => {
    displaySystemMessage('Partner disconnected');
    currentRoom = null;
});

// Handle ban
socket.on('banned', (data) => {
    displaySystemMessage(data.message);
    document.getElementById('message-input').disabled = true;
    document.getElementById('send-btn').disabled = true;
    
    // Start countdown timer
    let remainingTime = data.remaining_time;
    const timerDisplay = setInterval(() => {
        remainingTime--;
        if (remainingTime <= 0) {
            clearInterval(timerDisplay);
            document.getElementById('message-input').disabled = false;
            document.getElementById('send-btn').disabled = false;
            displaySystemMessage('Your ban has expired. Please be respectful.');
        } else {
            displaySystemMessage(`Ban remaining: ${Math.floor(remainingTime/60)}:${remainingTime%60}`);
        }
    }, 1000);
});

// Send message
function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (message && currentRoom) {
        socket.emit('message', { message });
        input.value = '';
    }
}

// Display message in chat
function displayMessage(message, isOwnMessage, timestamp) {
    const messagesDiv = document.getElementById('messages');
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(isOwnMessage ? 'own-message' : 'partner-message');
    
    messageElement.innerHTML = `
        <span class="message-content">${message}</span>
        <span class="timestamp">${timestamp}</span>
    `;
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Display system message
function displaySystemMessage(message) {
    const messagesDiv = document.getElementById('messages');
    const messageElement = document.createElement('div');
    messageElement.classList.add('system-message');
    messageElement.textContent = message;
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Event listeners
document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('message-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

document.getElementById('new-chat-btn').addEventListener('click', () => {
    location.reload();
});

// Check for existing ban on page load
if (userId) {
    fetch(`/check-ban/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.banned) {
                displaySystemMessage(`You are banned. Remaining time: ${Math.floor(data.remaining_time/60)}:${data.remaining_time%60}`);
                document.getElementById('message-input').disabled = true;
                document.getElementById('send-btn').disabled = true;
            }
        });
}