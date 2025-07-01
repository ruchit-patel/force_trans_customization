# Communication Hook for Issue Status Management

This module implements automatic issue status updates when support agents send emails to customers.

## Overview

When a support agent sends an email reply to a customer/lead from an issue, the system automatically changes the issue status to "Waiting on Customer". This helps track when the support team is waiting for a customer response.

## Implementation Details

### Files Created/Modified

1. **`communication.py`** - Main hook implementation
2. **`hooks.py`** - Hook registration
3. **`test_communication_hook.py`** - Test cases

### How It Works

1. **Hook Registration**: The `on_communication_after_insert` function is registered as a hook for the Communication doctype's `after_insert` event.

2. **Email Detection**: The system checks if the communication is:
   - Related to an Issue
   - An outgoing email (sent by support agent)
   - Sent to a customer/lead (not internal communication)

3. **Status Update**: If all conditions are met, the issue status is automatically changed to "Waiting on Customer".

### Key Functions

#### `on_communication_after_insert(doc, method)`
Main hook function that processes new communications and updates issue status.

#### `is_customer_email(communication_doc)`
Determines if an email is being sent to a customer by:
- Checking if recipient emails match the issue's `raised_by` field (most common case)
- Checking linked Lead's email_id
- Checking linked Contact's primary email
- Checking linked Customer's primary contact email
- Using domain-based detection for external emails

#### `update_issue_status_to_waiting(issue_name)`
Updates the issue status and adds a tracking comment.

### Email Detection Logic

The system identifies customer emails through multiple methods:

1. **Raised By Field**: Compares recipient emails with issue's `raised_by` field (most common case)
2. **Linked Lead**: Checks email from linked Lead's `email_id` field
3. **Linked Contact**: Checks primary email from linked Contact's email_ids table
4. **Linked Customer**: Checks primary email from Customer's primary contact
5. **Domain Detection**: Identifies external emails by comparing domains with company email accounts

### Benefits of Hook Approach

1. **Centralized Logic**: All email-related status changes are handled in one place
2. **Standard Frappe Pattern**: Uses Frappe's recommended hook system
3. **Comprehensive Coverage**: Catches all email communications, regardless of how they're sent
4. **Maintainable**: Easy to modify and extend
5. **Testable**: Can be easily unit tested

### Testing

Run the test file to verify functionality:
```bash
bench --site your-site.com console
```

Then run:
```python
exec(open('apps/force_trans_customization/force_trans_customization/custom/test_communication_hook.py').read())
```

### Configuration

No additional configuration is required. The hook automatically:
- Detects company email domains from Email Account settings
- Works with existing issue and communication workflows
- Maintains all existing functionality

### Error Handling

- Graceful error handling with logging
- Non-blocking operation (errors don't prevent email sending)
- Detailed error messages for debugging

### Future Enhancements

Potential improvements:
- Add configuration options for status mapping
- Support for different status transitions based on email content
- Integration with SLA tracking
- Email template-based status rules 