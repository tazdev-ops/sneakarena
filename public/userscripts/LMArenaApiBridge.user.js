// ==UserScript==
// @name         LMArena API Bridge
// @namespace    http://tampermonkey.net/
// @version      3.0.0
// @description  Bridge to connect LMArena with the API server
// @author       You
// @match        https://*.lmarena.ai/*
// @match        http://localhost:5173/*
// @match        http://127.0.0.1:5173/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Configuration
    const BRIDGE_HOST = 'ws://127.0.0.1:5102/internal/ws-debug';
    const MAX_RECONNECT_ATTEMPTS = 100;
    const RECONNECT_INTERVAL = 5000; // 5 seconds

    // State variables
    let ws = null;
    let reconnectAttempts = 0;
    let isConnected = false;
    let pendingRequests = new Map();
    let captureSessionIds = false;
    let capturedSessionId = null;
    let capturedMessageId = null;

    // DOM elements for status indicator
    let statusIndicator = null;

    // Create a status indicator in the page
    function createStatusIndicator() {
        if (statusIndicator) return;

        statusIndicator = document.createElement('div');
        statusIndicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 10000;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            background-color: #666;
            font-family: Arial, sans-serif;
        `;
        statusIndicator.textContent = 'Bridge: Disconnected';
        document.body.appendChild(statusIndicator);
    }

    // Update status indicator
    function updateStatus(status, color = '#666') {
        if (statusIndicator) {
            statusIndicator.textContent = `Bridge: ${status}`;
            statusIndicator.style.backgroundColor = color;
        }
    }

    // Connect to the bridge server
    function connect() {
        if (ws) {
            ws.close();
        }

        try {
            ws = new WebSocket(BRIDGE_HOST);

            ws.onopen = function(event) {
                console.log('Connected to LMArena Bridge');
                isConnected = true;
                reconnectAttempts = 0;
                updateStatus('Connected', '#4CAF50');

                // Send a simple hello message
                ws.send(JSON.stringify({
                    type: 'hello',
                    client_type: 'browser_script',
                    timestamp: Date.now()
                }));
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Received from bridge:', data);

                    // Handle different message types from the bridge
                    switch(data.type) {
                        case 'request':
                            handleBridgeRequest(data);
                            break;
                        case 'ping':
                            // Respond to keep alive
                            ws.send(JSON.stringify({type: 'pong'}));
                            break;
                        default:
                            console.log('Unknown message type from bridge:', data.type);
                    }
                } catch (error) {
                    console.error('Error processing message from bridge:', error);
                }
            };

            ws.onclose = function(event) {
                console.log('Disconnected from LMArena Bridge:', event.code, event.reason);
                isConnected = false;
                updateStatus('Disconnected', '#F44336');

                // Attempt to reconnect
                if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttempts++;
                    console.log(`Attempting to reconnect... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                    setTimeout(connect, RECONNECT_INTERVAL);
                } else {
                    console.error('Max reconnection attempts reached');
                    updateStatus('Failed to connect', '#F44336');
                }
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus('Error', '#F44336');
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            updateStatus('Connection Failed', '#F44336');
        }
    }

    // Handle requests coming from the bridge
    async function handleBridgeRequest(data) {
        const requestId = data.request_id;
        console.log(`Handling request ${requestId}:`, data);

        try {
            // Extract parameters from the bridge request
            const { conversation, model, temperature, top_p, max_tokens, stream } = data;

            // For now, we'll implement basic chat functionality
            // In a real implementation, this would interact with LMArena's actual API
            
            // Send an acknowledgment that the request was received
            if (ws && isConnected) {
                ws.send(JSON.stringify({
                    type: 'ack',
                    request_id: requestId,
                    status: 'received'
                }));
            }

            // For now, we'll simulate a response
            // In a real implementation, this would send the request to LMArena
            // and stream back the response
            
            if (stream) {
                // Simulate streaming response
                const responses = ["Hello", " from", " LMArena", " Bridge!"];
                for (let i = 0; i < responses.length; i++) {
                    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
                    
                    if (ws && isConnected) {
                        ws.send(JSON.stringify({
                            type: 'stream_chunk',
                            request_id: requestId,
                            content: responses[i],
                            is_final: i === responses.length - 1
                        }));
                    }
                }
            } else {
                // Simulate non-streaming response
                await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing time
                
                if (ws && isConnected) {
                    ws.send(JSON.stringify({
                        type: 'completion',
                        request_id: requestId,
                        content: "This is a simulated response from LMArena Bridge",
                        finish_reason: "stop"
                    }));
                }
            }
        } catch (error) {
            console.error(`Error handling request ${requestId}:`, error);
            
            if (ws && isConnected) {
                ws.send(JSON.stringify({
                    type: 'error',
                    request_id: requestId,
                    error: error.message
                }));
            }
        }
    }

    // Function to capture session IDs when the page loads or updates
    function captureCurrentIds() {
        if (!captureSessionIds) return;

        // Try to extract session information from the current page
        try {
            // This would depend on LMArena's actual structure
            // Look for elements that contain session information
            const urlParams = new URLSearchParams(window.location.search);
            const sessionId = urlParams.get('sessionId') || null;
            
            // Try to extract from page elements or state
            let messageElement = document.querySelector('[data-message-id]');
            let messageId = messageElement ? messageElement.getAttribute('data-message-id') : null;
            
            // If we found new IDs and they're different from captured ones
            if (sessionId && sessionId !== capturedSessionId) {
                capturedSessionId = sessionId;
                console.log('Captured Session ID:', sessionId);
                
                // Send to bridge if connected
                if (ws && isConnected) {
                    ws.send(JSON.stringify({
                        type: 'session_id_captured',
                        session_id: sessionId
                    }));
                }
            }
            
            if (messageId && messageId !== capturedMessageId) {
                capturedMessageId = messageId;
                console.log('Captured Message ID:', messageId);
                
                // Send to bridge if connected
                if (ws && isConnected) {
                    ws.send(JSON.stringify({
                        type: 'message_id_captured',
                        message_id: messageId
                    }));
                }
            }
        } catch (error) {
            console.error('Error capturing IDs:', error);
        }
    }

    // Function to enable ID capture mode
    function enableIdCapture() {
        captureSessionIds = true;
        console.log('ID capture mode enabled');
        updateStatus('Connected - Capturing IDs', '#2196F3');
    }

    // Function to disable ID capture mode
    function disableIdCapture() {
        captureSessionIds = false;
        console.log('ID capture mode disabled');
        updateStatus('Connected', '#4CAF50');
    }

    // Function to monitor page changes and capture IDs
    function setupPageMonitoring() {
        // Monitor for URL changes (single page applications)
        let currentUrl = location.href;
        const urlCheck = setInterval(() => {
            if (location.href !== currentUrl) {
                currentUrl = location.href;
                captureCurrentIds();
            }
        }, 1000);

        // Monitor for DOM changes that might contain new session info
        const observer = new MutationObserver((mutations) => {
            captureCurrentIds();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial capture
        captureCurrentIds();
    }

    // Add a function to the window object so it can be called from other scripts
    window.LMArenaBridge = {
        connect: connect,
        enableIdCapture: enableIdCapture,
        disableIdCapture: disableIdCapture,
        isConnected: () => isConnected,
        getStatus: () => ({ isConnected, capturedSessionId, capturedMessageId })
    };

    // Initialize the script
    function init() {
        console.log('LMArena Bridge userscript loaded');
        createStatusIndicator();
        connect();
        setupPageMonitoring();

        // Add a small delay before starting ID capture to ensure page is loaded
        setTimeout(() => {
            enableIdCapture();
        }, 2000);
    }

    // Start the script when the page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Add a small indicator to the page title to show the script is active
    const titleIndicator = document.createElement('span');
    titleIndicator.textContent = '🤖';
    titleIndicator.style.marginRight = '5px';
    if (document.titleElement) {
        document.titleElement.insertBefore(titleIndicator, document.titleElement.firstChild);
    } else {
        // For pages where we can't easily modify title, we'll just log
        console.log('LMArena Bridge active - look for status indicator in top-right corner');
    }
})();