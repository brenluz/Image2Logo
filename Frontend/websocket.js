// Create a WebSocket connection to the server
const socket = new WebSocket('ws://localhost:12345');

// Event listener for when the connection is opened
socket.addEventListener('open', () => {
    console.log('Connected to the WebSocket server');
});

// Event listener for when a message is received from the server
socket.addEventListener('message', (event) => {
    console.log('Message received from server:', event.data);
});

// Event listener for when the connection is closed
socket.addEventListener('close', () => {
    console.log('Disconnected from the WebSocket server');
});

// Event listener for when an error occurs
socket.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
});