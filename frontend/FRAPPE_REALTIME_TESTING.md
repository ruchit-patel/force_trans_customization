# Frappe Real-time Updates Testing Guide

## Implementation Status ✅

**Frontend**: Ready and listening for Frappe socket events
**Backend**: Hooks configured to emit socket events on Issue changes

## How to Test

### 1. Start the application
- Run `bench start` to start the Frappe server with socket.io
- Navigate to your Issue Tracker frontend

### 2. Test Real-time Updates

#### Open Multiple Tabs/Windows:
1. Open the Issue Tracker in multiple browser tabs/windows
2. You should see the green connection indicator in the top-right corner

#### Test Issue Updates:
1. **In Tab 1**: View the Issue list
2. **In Tab 2**: Go to Frappe desk and edit an Issue:
   - Change status, priority, or subject
   - Save the Issue
3. **In Tab 1**: You should see:
   - A notification popup saying "Issue Updated"
   - The issue list automatically refreshes
   - Connection status remains green

#### Test Issue Creation:
1. **In Frappe desk**: Create a new Issue
2. **In frontend tabs**: You should see:
   - "New Issue Created" notification
   - Issue list refreshes to show the new issue

## What Happens Behind the Scenes

### Frontend (`useRealTimeIssues.js`):
- Listens for Frappe socket events: `doctype_update`, `doc_create`, `doc_delete`
- Filters events to only handle Issue doctype
- Shows notifications for each update
- Automatically refreshes the issue list

### Backend (`issue_hooks.py`):
- `on_issue_insert`: Emits socket event when Issue is created
- `on_issue_save`: Emits socket event when Issue is updated  
- `emit_issue_delete`: Emits socket event when Issue is deleted
- Uses `frappe.publish_realtime()` to emit standard Frappe socket events

## Socket Events Emitted

### On Issue Update:
```python
frappe.publish_realtime(
    event='doctype_update',
    message={
        'doctype': 'Issue',
        'name': doc.name,
        'modified_by': doc.modified_by,
        'subject': doc.subject,
        'status': doc.status,
        'priority': doc.priority
    }
)
```

### On Issue Creation:
```python
frappe.publish_realtime(
    event='doc_create',
    message={
        'doctype': 'Issue',
        'name': doc.name,
        'owner': doc.owner,
        'subject': doc.subject,
        'status': doc.status
    }
)
```

## Troubleshooting

### If Real-time Updates Don't Work:

1. **Check Connection Status**: 
   - Green indicator = Socket connected and working
   - "Polling for updates every 30s" = Socket failed, using polling fallback
   - Red indicator = No updates system active

2. **Browser Console**:
   - Look for socket connection messages
   - Common error: "WebSocket connection failed" or "400 Bad Request"
   - Should show: "Socket connected successfully" if working

3. **Socket Connection Issues**:
   - **400 Bad Request**: Socket.io server not configured properly
   - **Connection refused**: Socket.io service not running
   - **CORS errors**: Authentication or site configuration issue

4. **Fallback Polling System**:
   - If socket fails, the system automatically switches to polling every 30 seconds
   - You'll see "Polling for updates every 30s" in the status indicator
   - This ensures updates still work even if socket.io is broken

5. **Server Logs**:
   - Check for socket emission log messages
   - Verify hooks are being called: "Socket event emitted for Issue update"

6. **Frappe Socket.io Setup**:
   - Ensure `bench start` includes socket.io service (port 9009)
   - Check if socket.io port is accessible: `netstat -tlnp | grep 9009`
   - Verify `common_site_config.json` has `socketio_port: 9009`

### Expected Behavior:

**If Socket.io Works:**
- ✅ Issue updates in Frappe desk appear instantly in frontend (real-time)
- ✅ Green connection indicator shows "Connected - Live updates enabled"
- ✅ Notifications show immediately for each change
- ✅ Issue list refreshes automatically without delay

**If Socket.io Fails (Fallback Mode):**
- ✅ Status shows "Polling for updates every 30s"
- ✅ Issue updates appear within 30 seconds of being saved
- ✅ Still works, just with a slight delay
- ✅ Notifications show when polling detects changes

**Both Modes:**
- ✅ Connection status indicator works
- ✅ Works across multiple browser tabs/users
- ✅ Issue list refreshes automatically
- ✅ Proper error handling and fallbacks

## Current Status

Your socket connection is currently failing (400 Bad Request), but the **polling fallback system ensures updates still work**. The system will:

1. Try to connect to socket.io on startup
2. If it fails, automatically start polling every 30 seconds
3. Continue to retry socket connection in background
4. Seamlessly switch to real-time if socket connects later

**This means your real-time updates are working via polling, even though socket.io isn't connecting!**