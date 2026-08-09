/**
 * test/nexusBridge.test.js
 * 
 * Tests the real-time, bidirectional data synchronization bridge, 
 * including message forwarding, queueing/buffering, and reconnection.
 */

const { expect } = require('chai');
const WebSocket = require('ws');
const NexusBridge = require('../src/api/nexusBridge');

describe('NexusBridge Real-time Data Sync', () => {
    let primaryMockServer;
    let cryptoMockServer;
    let bridge;

    let primaryClientWs;
    let cryptoClientWs;

    let primaryReceived = [];
    let cryptoReceived = [];

    // Helper to start mock WebSocket servers
    const startMockServers = () => {
        primaryMockServer = new WebSocket.Server({ port: 8081 });
        cryptoMockServer = new WebSocket.Server({ port: 8082 });

        primaryMockServer.on('connection', (ws) => {
            primaryClientWs = ws;
            ws.on('message', (msg) => {
                primaryReceived.push(msg.toString());
            });
        });

        cryptoMockServer.on('connection', (ws) => {
            cryptoClientWs = ws;
            ws.on('message', (msg) => {
                cryptoReceived.push(msg.toString());
            });
        });
    };

    // Helper to close mock WebSocket servers
    const stopMockServers = (done) => {
        if (primaryMockServer) primaryMockServer.close();
        if (cryptoMockServer) cryptoMockServer.close();
        setTimeout(done, 100);
    };

    beforeEach((done) => {
        primaryReceived = [];
        cryptoReceived = [];
        startMockServers();
        done();
    });

    afterEach((done) => {
        if (bridge) {
            bridge.stop();
        }
        stopMockServers(done);
    });

    it('should successfully establish connections and forward messages bidirectionally', function(done) {
        this.timeout(5000);

        bridge = new NexusBridge({
            primaryWsUrl: 'ws://localhost:8081',
            cryptoWsUrl: 'ws://localhost:8082',
            heartbeatInterval: 100000, // Large to avoid interferes
            fallbackPollInterval: 100000
        });

        bridge.start();

        // Wait for connections to open
        setTimeout(() => {
            // Send message from Primary Mock to Bridge (which forwards to Crypto)
            if (primaryClientWs) {
                primaryClientWs.send('Hello from Primary Network');
            }

            setTimeout(() => {
                expect(cryptoReceived).to.include('Hello from Primary Network');

                // Send message from Crypto Mock to Bridge (which forwards to Primary)
                if (cryptoClientWs) {
                    cryptoClientWs.send('Hello from Crypto Network');
                }

                setTimeout(() => {
                    expect(primaryReceived).to.include('Hello from Crypto Network');
                    done();
                }, 500);
            }, 500);
        }, 1000);
    });

    it('should queue messages when a server is offline and flush them upon reconnection', function(done) {
        this.timeout(10000);

        bridge = new NexusBridge({
            primaryWsUrl: 'ws://localhost:8081',
            cryptoWsUrl: 'ws://localhost:8082',
            heartbeatInterval: 100000,
            fallbackPollInterval: 100000,
            maxReconnectInterval: 1000
        });

        bridge.start();

        setTimeout(() => {
            // Close the Crypto mock server to simulate disconnect
            if (cryptoMockServer) {
                cryptoMockServer.close();
            }

            setTimeout(() => {
                // Send a message from Primary Mock to the bridge
                if (primaryClientWs) {
                    primaryClientWs.send('Buffered transaction message');
                }

                setTimeout(() => {
                    // Re-start Crypto mock server on the same port
                    cryptoMockServer = new WebSocket.Server({ port: 8082 });
                    cryptoMockServer.on('connection', (ws) => {
                        cryptoClientWs = ws;
                        ws.on('message', (msg) => {
                            cryptoReceived.push(msg.toString());
                        });
                    });

                    // Wait for bridge to reconnect and flush the queue
                    setTimeout(() => {
                        expect(cryptoReceived).to.include('Buffered transaction message');
                        done();
                    }, 3500);
                }, 1000);
            }, 1000);
        }, 1000);
    });
});
