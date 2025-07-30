# Real-Time Updates Setup Guide

This document outlines the server-side implementation needed to support the real-time features in the Issue Tracker frontend.

## Frontend Implementation Status ✅

The frontend is now fully configured with:
- Socket.io client integration
- Real-time issue updates composable (`useRealTimeIssues.js`)
- Conflict resolution UI
- Live notifications system
- Connected users tracking

## Required Server-Side Implementation

### 1. Socket.io Server Setup

The backend needs to implement socket.io server endpoints to emit the following events:

```python
# Example Python/Frappe implementation structure

# Events to emit to clients:
- 'issue_created': When a new issue is created
- 'issue_updated': When an issue is modified  
- 'issue_deleted': When an issue is deleted
- 'user_joined': When a user joins the application
- 'user_left': When a user leaves the application
- 'issue_conflict': When concurrent modifications are detected
```

### 2. Event Data Structure

#### Issue Created Event
```javascript
{
  issue: {
    name: "ISSUE-001",
    subject: "Bug in login system",
    status: "Open",
    priority: "High",
    // ... other issue fields
  },
  user: "john.doe@company.com",
  timestamp: "2024-01-15T10:30:00Z"
}
```

#### Issue Updated Event
```javascript
{
  issue: {
    name: "ISSUE-001", 
    subject: "Updated bug in login system",
    // ... updated fields
  },
  user: "jane.smith@company.com",
  changes: {
    status: "In Progress",
    assignee: "dev.team@company.com"
  },
  conflict: false, // or true if concurrent modification detected
  timestamp: "2024-01-15T10:35:00Z"
}
```

#### Conflict Detection Event
```javascript
{
  issue: {
    name: "ISSUE-001",
    // ... current issue state
  },
  user: "other.user@company.com",
  localChanges: {
    status: "Resolved"
  },
  remoteChanges: {
    status: "In Progress",
    assignee: "different.user@company.com"
  },
  timestamp: "2024-01-15T10:36:00Z"
}
```

### 3. Integration Points

#### Document Hooks (Frappe)
Add socket emissions in Issue doctype hooks:

```python
# In issue.py or hooks.py

def on_create(doc, method):
    emit_socket_event('issue_created', {
        'issue': doc.as_dict(),
        'user': frappe.session.user,
        'timestamp': now()
    })

def on_update(doc, method):
    # Check for conflicts here
    emit_socket_event('issue_updated', {
        'issue': doc.as_dict(), 
        'user': frappe.session.user,
        'changes': get_changes(doc),
        'conflict': detect_conflict(doc),
        'timestamp': now()
    })

def on_delete(doc, method):
    emit_socket_event('issue_deleted', {
        'issue': doc.as_dict(),
        'user': frappe.session.user,
        'timestamp': now()
    })
```

#### User Session Management
Track user connections and emit join/leave events:

```python
def on_user_connect(user_id):
    emit_socket_event('user_joined', {
        'user': {
            'id': user_id,
            'name': get_user_name(user_id)
        },
        'timestamp': now()
    })

def on_user_disconnect(user_id):
    emit_socket_event('user_left', {
        'user': {
            'id': user_id,
            'name': get_user_name(user_id)
        },
        'timestamp': now()
    })
```

### 4. Conflict Detection Logic

Implement server-side conflict detection:

```python
def detect_conflict(doc):
    # Compare doc modification time with client's last known version
    # Check if multiple users modified the same fields
    # Return True if conflict detected
    pass

def get_changes(doc):
    # Return dictionary of changed fields
    # Compare current doc with previous version
    pass
```

### 5. Room Management (Optional)

For better performance, implement room-based updates:

```python
# Users can join specific issue rooms
def join_issue_room(user_id, issue_id):
    # Add user to issue-specific room
    pass

def leave_issue_room(user_id, issue_id):
    # Remove user from issue-specific room  
    pass

# Emit events only to users in relevant rooms
def emit_to_issue_room(issue_id, event, data):
    # Emit to users watching this specific issue
    pass
```

## Testing the Implementation

### Manual Testing
1. Open multiple browser tabs/windows
2. Create/modify issues in one tab
3. Verify real-time updates appear in other tabs
4. Test conflict scenarios by simultaneous edits

### Frontend Testing Features
The frontend includes:
- Connection status indicator
- Real-time notifications for all events
- Conflict resolution modals
- Connected users sidebar
- Automatic data refresh on updates

## Security Considerations

1. **Authentication**: Ensure socket connections are authenticated
2. **Authorization**: Verify users can only receive updates for issues they have access to
3. **Rate Limiting**: Implement rate limiting to prevent spam
4. **Data Validation**: Validate all incoming socket data

## Performance Optimization

1. **Room-based Updates**: Only send updates to relevant users
2. **Debouncing**: Prevent excessive update frequency
3. **Connection Management**: Handle reconnections gracefully
4. **Memory Management**: Clean up disconnected users

---

The frontend is ready to receive and handle all these real-time events once the server-side implementation is complete.