// Realtime testing utilities
// These functions will be available in the browser console

export function testRealtimeConnection() {
    console.log('=== Testing Realtime Connection ===');
    
    // Get the socket instance from the global scope
    const socket = window.socket;
    
    if (!socket) {
        console.error('❌ No socket connection found');
        console.log('💡 Make sure you are on the issue tracker page');
        return;
    }
    
    console.log('✅ Socket found:', socket.id);
    console.log('✅ Socket connected:', socket.connected);
    
    // Listen for all events for 30 seconds
    const eventListener = (eventName, ...args) => {
        if (eventName.includes('list_update') || eventName.includes('Issue') || eventName.includes('doc_')) {
            console.log('🔥 Received event:', eventName, args);
        }
    };
    
    socket.onAny(eventListener);
    
    console.log('👂 Listening for relevant events for 30 seconds...');
    
    setTimeout(() => {
        socket.offAny(eventListener);
        console.log('⏰ Stopped listening for events');
    }, 30000);
    
    return socket;
}

export function testBackendEmission() {
    console.log('💡 Testing backend emission...');
    
    // Use fetch to call the backend API
    fetch('/api/method/force_trans_customization.api.test_realtime.test_realtime_emission', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': window.csrf_token || ''
        },
        credentials: 'include'
    })
    .then(response => response.json())
    .then(result => {
        console.log('📤 Backend test emission result:', result);
    })
    .catch(error => {
        console.error('❌ Backend test emission failed:', error);
    });
}

export function createTestIssue() {
    console.log('🆕 Creating test issue...');
    
    fetch('/api/method/force_trans_customization.api.test_realtime.create_test_issue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': window.csrf_token || ''
        },
        credentials: 'include'
    })
    .then(response => response.json())
    .then(result => {
        console.log('✅ Test issue created:', result);
        if (result.message && result.message.issue_name) {
            setTimeout(() => {
                updateTestIssue(result.message.issue_name);
            }, 2000);
        }
    })
    .catch(error => {
        console.error('❌ Failed to create test issue:', error);
    });
}

export function updateTestIssue(issueName) {
    console.log('📝 Updating test issue:', issueName);
    
    fetch('/api/method/force_trans_customization.api.test_realtime.update_test_issue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': window.csrf_token || ''
        },
        body: JSON.stringify({
            issue_name: issueName
        }),
        credentials: 'include'
    })
    .then(response => response.json())
    .then(result => {
        console.log('✅ Test issue updated:', result);
    })
    .catch(error => {
        console.error('❌ Failed to update test issue:', error);
    });
}

// Make functions available globally for console testing
if (typeof window !== 'undefined') {
    window.testRealtimeConnection = testRealtimeConnection;
    window.testBackendEmission = testBackendEmission;
    window.createTestIssue = createTestIssue;
    window.updateTestIssue = updateTestIssue;
}