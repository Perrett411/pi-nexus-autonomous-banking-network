const WebSocket = require('ws');
const NexusBridge = require('./nexusBridge');

const wss = new WebSocket.Server({ port: 8080 });

const start = () => {
    wss.on('connection', (ws) => {
        console.log('New client connected');

        ws.on('message', (message) => {
            console.log(`Received: ${message}`);
            // Broadcast to all clients
            wss.clients.forEach((client) => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(message);
                }
            });
        });

        ws.on('close', () => {
            console.log('Client disconnected');
        });
    });

    console.log('WebSocket server is running on ws://localhost:8080');

    // Instantiate and start the real-time bidirectional data channel bridge
    const nexusBridge = new NexusBridge();
    nexusBridge.start();
};

module.exports = { start };
