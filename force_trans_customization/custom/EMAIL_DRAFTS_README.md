# Email Draft Functionality

This module adds server-side email draft functionality to Frappe/ERPNext, allowing users to save email drafts that persist across browser sessions and are visible in the issue timeline.

## Features

- ✅ **Server-side Draft Storage**: Drafts are saved as Communication documents with "Draft" status
- ✅ **Timeline Integration**: Drafts appear in the issue timeline with edit/send/delete actions
- ✅ **Cross-device Access**: Drafts are accessible from any device
- ✅ **Continue Editing**: Users can continue editing drafts from the timeline
- ✅ **Send Drafts**: Direct send functionality from timeline
- ✅ **Delete Drafts**: Remove unwanted drafts
- ✅ **Auto-save**: Drafts are automatically saved as you type

## How It Works

### 1. Draft Creation
When a user starts composing an email in the CommunicationComposer:
- The `save_as_draft()` method is overridden to save to server instead of local storage
- Drafts are created as Communication documents with status "Draft"
- Only one draft per user per document is maintained (updates existing draft)

### 2. Timeline Display
Drafts appear in the issue timeline with:
- Distinct visual styling (warning icon, "Draft" label)
- Subject, recipients, and content preview
- Action buttons: Continue Editing, Send, Delete

### 3. Draft Management
- **Continue Editing**: Opens the CommunicationComposer with draft content
- **Send**: Converts draft to regular Communication and sends email
- **Delete**: Removes the draft permanently

## Files Created/Modified

### Server-side
- `api/email_draft.py` - API endpoints for draft operations
- `patches/v1_0_add_draft_status.py` - Patch to add "Draft" status to Communication doctype
- `patches.txt` - Updated to include the patch

### Client-side
- `public/js/communication_draft.js` - Enhanced CommunicationComposer functionality
- `public/js/enhanced_timeline.js` - Timeline integration for drafts
- `hooks.py` - Updated to include new JavaScript files

## API Endpoints

### `save_draft(**kwargs)`
Saves email content as a draft Communication document.

**Parameters:**
- `doctype`: Reference document type
- `docname`: Reference document name
- `subject`: Email subject
- `content`: Email content
- `recipients`: Email recipients
- `cc`: CC recipients
- `bcc`: BCC recipients
- `sender`: Email sender
- `email_template`: Email template

### `get_drafts(doctype, docname)`
Retrieves all drafts for a specific document.

### `send_draft(draft_name)`
Sends a draft email and converts it to a regular Communication.

### `delete_draft(draft_name)`
Deletes a draft Communication.

### `continue_editing_draft(draft_name)`
Retrieves draft data for editing in the CommunicationComposer.

## Usage

### For Users
1. **Compose Email**: Start composing an email from any document (e.g., Issue)
2. **Auto-save**: Drafts are automatically saved as you type
3. **View Drafts**: Drafts appear in the document timeline
4. **Continue Editing**: Click "Continue Editing" to resume composition
5. **Send**: Click "Send" to send the draft email
6. **Delete**: Click "Delete" to remove unwanted drafts

### For Developers
The functionality is automatically available for all documents that support email composition. No additional configuration is required.

## Installation

1. Install the `force_trans_customization` app
2. Run `bench migrate` to apply the patch
3. Restart the Frappe server

## Customization

### Adding Draft Support to Other Documents
The functionality works automatically for any document that uses the CommunicationComposer. No additional code is required.

### Customizing Draft Appearance
Modify the `add_draft_to_timeline()` method in `communication_draft.js` to customize the visual appearance of drafts in the timeline.

### Adding Custom Actions
Extend the draft functionality by adding new API endpoints and corresponding client-side methods.

## Troubleshooting

### Drafts Not Appearing in Timeline
- Check if the patch was applied successfully
- Verify that "Draft" status exists in Communication doctype
- Check browser console for JavaScript errors

### Draft Save Errors
- Check server logs for API errors
- Verify user permissions for Communication doctype
- Ensure database connectivity

### Timeline Not Refreshing
- Check if the enhanced timeline JavaScript is loaded
- Verify that the timeline refresh method is being called
- Check for JavaScript errors in browser console

## Security

- Users can only access their own drafts
- Draft operations require appropriate permissions
- All API endpoints are properly validated
- Drafts are subject to the same permission rules as regular Communications 