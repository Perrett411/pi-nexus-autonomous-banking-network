/**
 * nexusBridge.js
 * 
 * Establishes real-time, bidirectional data synchronization between:
 * - https://postman-echo.com (Primary AI Bank Network Mock Gateway)
 * - https://ws.postman-echo.com (Crypto AI Bank Network Mock Gateway)
 * 
 * Supports robust connection management, heartbeats, message queuing/buffering, 
 * exponential backoff reconnection, and REST-based fallback synchronization.
 */

const WebSocket = require('ws');
const axios = require('axios');

class NexusBridge {
    constructor(config = {}) {
        this.primaryWsUrl = config.primaryWsUrl || 'wss://ws.postman-echo.com/raw';
        this.cryptoWsUrl = config.cryptoWsUrl || 'wss://echo.websocket.org';
        
        this.primaryHttpUrl = config.primaryHttpUrl || 'https://postman-echo.com/get';
        this.cryptoHttpUrl = config.cryptoHttpUrl || 'https://postman-echo.com/post';

        this.primaryWs = null;
        this.cryptoWs = null;

        this.primaryQueue = [];
        this.cryptoQueue = [];
        this.maxQueueSize = config.maxQueueSize || 500;

        this.reconnectIntervals = { primary: 1000, crypto: 1000 };
        this.maxReconnectInterval = config.maxReconnectInterval || 30000;
        this.reconnectBackoffFactor = config.reconnectBackoffFactor || 2;

        this.fallbackPollInterval = config.fallbackPollInterval || 10000; // 10 seconds
        this.pollTimer = null;
        this.heartbeatInterval = config.heartbeatInterval || 30000; // 30 seconds
        this.heartbeatTimer = null;

        this.isStarted = false;
    }

    /**
     * Start the bridge.
     */
    start() {
        if (this.isStarted) {
            console.log('[NexusBridge] Bridge is already running.');
            return;
        }

        console.log('[NexusBridge] Starting real-time bidirectional sync bridge...');
        this.isStarted = true;

        this.connectPrimary();
        this.connectCrypto();

        this.startHeartbeat();
        this.startFallbackPoll();
    }

    /**
     * Connect to the Primary AI Bank Network WebSocket.
     */
    connectPrimary() {
        console.log(`[NexusBridge] Connecting to Primary WS: ${this.primaryWsUrl}`);
        this.primaryWs = new WebSocket(this.primaryWsUrl);

        this.primaryWs.on('open', () => {
            console.log('[NexusBridge] Successfully connected to Primary WS.');
            this.reconnectIntervals.primary = 1000; // Reset reconnect backoff
            this.flushQueue('primary');
        });

        this.primaryWs.on('message', (data) => {
            const message = data.toString();
            console.log(`[NexusBridge] Received message from Primary WS: ${message}`);
            this.forwardToCrypto(message);
        });

        this.primaryWs.on('error', (err) => {
            console.error('[NexusBridge] Primary WS error:', err.message);
        });

        this.primaryWs.on('close', (code, reason) => {
            console.warn(`[NexusBridge] Primary WS connection closed. Code: ${code}, Reason: ${reason}`);
            if (this.isStarted) {
                this.scheduleReconnection('primary');
            }
        });
    }

    /**
     * Connect to the Crypto AI Bank Network WebSocket.
     */
    connectCrypto() {
        console.log(`[NexusBridge] Connecting to Crypto WS: ${this.cryptoWsUrl}`);
        this.cryptoWs = new WebSocket(this.cryptoWsUrl);

        this.cryptoWs.on('open', () => {
            console.log('[NexusBridge] Successfully connected to Crypto WS.');
            this.reconnectIntervals.crypto = 1000; // Reset reconnect backoff
            this.flushQueue('crypto');
        });

        this.cryptoWs.on('message', (data) => {
            const message = data.toString();
            console.log(`[NexusBridge] Received message from Crypto WS: ${message}`);
            this.forwardToPrimary(message);
        });

        this.cryptoWs.on('error', (err) => {
            console.error('[NexusBridge] Crypto WS error:', err.message);
        });

        this.cryptoWs.on('close', (code, reason) => {
            console.warn(`[NexusBridge] Crypto WS connection closed. Code: ${code}, Reason: ${reason}`);
            if (this.isStarted) {
                this.scheduleReconnection('crypto');
            }
        });
    }

    /**
     * Schedule reconnection with exponential backoff.
     */
    scheduleReconnection(target) {
        const currentInterval = this.reconnectIntervals[target];
        console.log(`[NexusBridge] Scheduling ${target} reconnection in ${currentInterval}ms...`);
        
        setTimeout(() => {
            if (!this.isStarted) return;
            if (target === 'primary') {
                this.connectPrimary();
            } else {
                this.connectCrypto();
            }
        }, currentInterval);

        // Exponential backoff
        this.reconnectIntervals[target] = Math.min(
            currentInterval * this.reconnectBackoffFactor,
            this.maxReconnectInterval
        );
    }

    /**
     * Forward message to Crypto WS. If down, queue it.
     */
    forwardToCrypto(message) {
        if (this.cryptoWs && this.cryptoWs.readyState === WebSocket.OPEN) {
            try {
                this.cryptoWs.send(message);
                console.log('[NexusBridge] Message forwarded successfully to Crypto WS.');
            } catch (err) {
                console.error('[NexusBridge] Failed to forward message to Crypto WS, queueing instead:', err.message);
                this.enqueue('crypto', message);
            }
        } else {
            console.warn('[NexusBridge] Crypto WS is not connected. Message queued.');
            this.enqueue('crypto', message);
        }
    }

    /**
     * Forward message to Primary WS. If down, queue it.
     */
    forwardToPrimary(message) {
        if (this.primaryWs && this.primaryWs.readyState === WebSocket.OPEN) {
            try {
                this.primaryWs.send(message);
                console.log('[NexusBridge] Message forwarded successfully to Primary WS.');
            } catch (err) {
                console.error('[NexusBridge] Failed to forward message to Primary WS, queueing instead:', err.message);
                this.enqueue('primary', message);
            }
        } else {
            console.warn('[NexusBridge] Primary WS is not connected. Message queued.');
            this.enqueue('primary', message);
        }
    }

    /**
     * Add message to specified target's queue.
     */
    enqueue(target, message) {
        const queue = target === 'primary' ? this.primaryQueue : this.cryptoQueue;
        if (queue.length >= this.maxQueueSize) {
            queue.shift(); // Evict oldest if queue size exceeded
            console.warn(`[NexusBridge] ${target} queue full. Evicted oldest message.`);
        }
        queue.push(message);
    }

    /**
     * Flush buffered messages once connection is restored.
     */
    flushQueue(target) {
        const queue = target === 'primary' ? this.primaryQueue : this.cryptoQueue;
        const ws = target === 'primary' ? this.primaryWs : this.cryptoWs;

        if (queue.length === 0) return;
        console.log(`[NexusBridge] Flushing ${queue.length} buffered messages to ${target} WS...`);

        while (queue.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
            const msg = queue[0];
            try {
                ws.send(msg);
                queue.shift();
            } catch (err) {
                console.error(`[NexusBridge] Error flushing message to ${target} WS:`, err.message);
                break;
            }
        }
    }

    /**
     * Active connection health checks via Ping-Pong.
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (!this.isStarted) return;
            
            // Ping Primary WS
            if (this.primaryWs && this.primaryWs.readyState === WebSocket.OPEN) {
                try {
                    this.primaryWs.ping();
                } catch (err) {
                    console.error('[NexusBridge] Error pinging Primary WS:', err.message);
                }
            }
            
            // Ping Crypto WS
            if (this.cryptoWs && this.cryptoWs.readyState === WebSocket.OPEN) {
                try {
                    this.cryptoWs.ping();
                } catch (err) {
                    console.error('[NexusBridge] Error pinging Crypto WS:', err.message);
                }
            }
        }, this.heartbeatInterval);
    }

    /**
     * Fallback poll mechanism via REST APIs when WebSocket isn't available.
     */
    startFallbackPoll() {
        this.pollTimer = setInterval(async () => {
            if (!this.isStarted) return;

            // Only run HTTP poll sync if either WebSocket is disconnected to act as backup
            const primaryConnected = this.primaryWs && this.primaryWs.readyState === WebSocket.OPEN;
            const cryptoConnected = this.cryptoWs && this.cryptoWs.readyState === WebSocket.OPEN;

            if (!primaryConnected || !cryptoConnected) {
                console.log('[NexusBridge] WebSocket channel down. Initiating backup REST synchronization...');
                try {
                    await this.syncRESTChannels();
                } catch (err) {
                    console.error('[NexusBridge] Backup REST synchronization failed:', err.message);
                }
            }
        }, this.fallbackPollInterval);
    }

    /**
     * Sync data between HTTP endpoints as fallback.
     */
    async syncRESTChannels() {
        // Step 1: Pull from Primary, Push to Crypto
        try {
            const primaryResponse = await axios.get(this.primaryHttpUrl, { timeout: 3000 });
            if (primaryResponse.data && primaryResponse.data.updates) {
                const updates = primaryResponse.data.updates;
                console.log(`[NexusBridge REST] Pulled ${updates.length} updates from Primary. Syncing with Crypto in parallel...`);
                await Promise.all(updates.map(update => 
                    axios.post(this.cryptoHttpUrl, update, { timeout: 3000 })
                ));
            }
        } catch (err) {
            console.warn('[NexusBridge REST] Primary -> Crypto HTTP Sync skipped or failed:', err.message);
        }

        // Step 2: Pull from Crypto, Push to Primary
        try {
            const cryptoResponse = await axios.get(this.cryptoHttpUrl, { timeout: 3000 });
            if (cryptoResponse.data && cryptoResponse.data.updates) {
                const updates = cryptoResponse.data.updates;
                console.log(`[NexusBridge REST] Pulled ${updates.length} updates from Crypto. Syncing with Primary in parallel...`);
                await Promise.all(updates.map(update => 
                    axios.post(this.primaryHttpUrl, update, { timeout: 3000 })
                ));
            }
        } catch (err) {
            console.warn('[NexusBridge REST] Crypto -> Primary HTTP Sync skipped or failed:', err.message);
        }
    }

    /**
     * Stop the bridge and clear all timers.
     */
    stop() {
        console.log('[NexusBridge] Stopping real-time bidirectional sync bridge...');
        this.isStarted = false;

        if (this.pollTimer) clearInterval(this.pollTimer);
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);

        if (this.primaryWs) {
            try {
                this.primaryWs.close();
            } catch (e) {}
            this.primaryWs = null;
        }

        if (this.cryptoWs) {
            try {
                this.cryptoWs.close();
            } catch (e) {}
            this.cryptoWs = null;
        }
    }
}

module.exports = NexusBridge;
