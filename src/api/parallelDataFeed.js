/**
 * parallelDataFeed.js
 *
 * QCF-driven parallel/mirror data feed channels between:
 * - https://nexus-x-aibank.com (Primary AI Bank Network)
 * - https://nexus-x-aibank-crypto.base44.app (Crypto AI Bank Network)
 *
 * Runs two redundant NexusBridge channels in parallel ("A" primary channel and
 * "B" mirror channel), so every banking and crypto update travels over mirrored
 * paths for accuracy. Each channel provides:
 *   - Real-time bidirectional WebSocket streaming (both directions of each network)
 *   - REST bridge fallback sync when its WebSocket connection is down
 *   - QCF-driven scheduled reconciliation sync to keep the mirrored copies accurate
 *
 * Environment overrides (see env.example):
 *   NEXUS_PRIMARY_WS_URL, NEXUS_CRYPTO_WS_URL,
 *   NEXUS_PRIMARY_HTTP_URL, NEXUS_CRYPTO_HTTP_URL
 */

const WebSocket = require('ws');
const NexusBridge = require('./nexusBridge');

class ParallelNexusDataFeed {
    constructor(config = {}) {
        // Channel A — primary data channel
        this.channelA = new NexusBridge({ ...config, channelId: 'A' });

        // Channel B — mirror data channel. Stagger its scheduled reconciliation
        // by half an interval so the mirrored channels never sync at the same moment.
        const baseInterval = config.scheduledSyncInterval || 60000;
        this.channelB = new NexusBridge({
            ...config,
            channelId: 'B',
            scheduledSyncInterval: baseInterval,
            syncStartDelay: Math.floor(baseInterval / 2)
        });
    }

    /**
     * Start both parallel/mirror channels.
     */
    start() {
        console.log('[ParallelNexusDataFeed] Starting QCF-driven parallel/mirror data feed channels...');
        this.channelA.start();
        this.channelB.start();
    }

    /**
     * Trigger an immediate QCF reconciliation sync on both channels.
     */
    async syncNow() {
        await Promise.all([
            this.channelA.syncRESTChannels(),
            this.channelB.syncRESTChannels()
        ]);
    }

    /**
     * Health/status report for both parallel channels.
     */
    getStatus() {
        const channelStatus = (bridge) => ({
            channelId: bridge.channelId,
            primaryWsUrl: bridge.primaryWsUrl,
            cryptoWsUrl: bridge.cryptoWsUrl,
            primaryWsConnected: !!(bridge.primaryWs && bridge.primaryWs.readyState === WebSocket.OPEN),
            cryptoWsConnected: !!(bridge.cryptoWs && bridge.cryptoWs.readyState === WebSocket.OPEN),
            queuedMessages: {
                primary: bridge.primaryQueue.length,
                crypto: bridge.cryptoQueue.length
            },
            lastSync: bridge.lastSync
        });

        return {
            primaryNetwork: 'https://nexus-x-aibank.com',
            cryptoNetwork: 'https://nexus-x-aibank-crypto.base44.app',
            channels: [channelStatus(this.channelA), channelStatus(this.channelB)]
        };
    }

    /**
     * Stop both parallel/mirror channels and clear all timers.
     */
    stop() {
        console.log('[ParallelNexusDataFeed] Stopping QCF-driven parallel/mirror data feed channels...');
        this.channelA.stop();
        this.channelB.stop();
    }
}

module.exports = { ParallelNexusDataFeed, NexusBridge };
