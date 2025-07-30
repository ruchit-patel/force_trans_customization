# Testing the New Realtime List Updates

## Overview

We've implemented a Frappe-style realtime list update system that's much cleaner than the previous custom hooks approach. The new system:

1. **Uses standard Frappe events**: Publishes `list_update` events that follow Frappe's pattern
2. **Debounced updates**: Batches updates similar to Frappe's list view (2s normal, 15s for large tables)
3. **Smart filtering**: Only updates when appropriate (not during bulk operations, filter editing, etc.)
4. **Clean architecture**: Single composable handles all realtime logic

## Files Changed

### Backend (Python)
- `issue_list_hooks.py` - New clean hooks that emit `list_update` events
- `hooks.py` - Updated to use new hooks instead of old ones

### Frontend (Vue.js)
- `useIssueListUpdates.js` - New composable following Frappe's pattern
- `IssueTracker.vue` - Updated to use new composable with notifications

## Testing Instructions

1. **Start the application**:
   ```bash
   bench start
   ```

2. **Open the Issue Tracker** in your browser:
   - Navigate to `/frontend` or the Issue Tracker page
   - Check that the realtime status shows "Listening for list_update events"

3. **Test realtime updates**:
   - Open ERPNext in another tab/browser
   - Go to Issue List (or create/edit Issues via API)
   - Make changes to Issues:
     - Create a new Issue
     - Update an existing Issue
     - Change status, priority, etc.
     - Delete an Issue

4. **Expected behavior**:
   - The frontend should show "X updates pending..." briefly
   - After 2 seconds (debounce), the list should refresh automatically
   - A notification should appear showing which issues were updated
   - The list should reflect the changes without manual refresh

## Key Improvements

### ✅ What's Better Now

1. **Standard Events**: Uses Frappe's built-in `list_update` event instead of custom events
2. **Cleaner Code**: Much simpler hooks and frontend logic
3. **Better Performance**: Debounced updates prevent excessive refreshing
4. **Consistent Pattern**: Follows Frappe's own list view update pattern
5. **Less Coupling**: Frontend doesn't depend on custom backend events

### 🗑️ What We Removed

1. **Custom socket events**: No more `doctype_update`, `Issue_update`, etc.
2. **Complex event handling**: Simplified to just listen for `list_update`
3. **Old hooks file**: `issue_hooks.py` is replaced by `issue_list_hooks.py`
4. **Polling fallback**: Since we're using Frappe's standard pattern, it's more reliable

## Troubleshooting

### Issue List Not Updating
1. Check browser console for socket connection errors
2. Verify that the realtime status shows as connected
3. Check Frappe logs for hook execution errors
4. Try the manual refresh button

### Socket Connection Issues
1. Ensure `socketio_port` is correct in `common_site_config.json`
2. Check that Redis is running (required for Frappe realtime)
3. Verify no firewall is blocking the websocket port

### Events Not Being Emitted
1. Check Python console/logs for hook errors
2. Verify the new hooks are properly registered in `hooks.py`
3. Test by manually triggering Issue operations in ERPNext

## Next Steps

1. **Remove old files**: Once confirmed working, delete `issue_hooks.py`
2. **Add more refinements**: Could add user-specific filtering, bulk operation detection, etc.
3. **Extend to other doctypes**: Apply the same pattern to other document types if needed