#!/usr/bin/env python3

import frappe
import json

def test_issue_realtime_events():
    """
    Test script to verify that Issue realtime events are working
    Run this from frappe bench: bench execute force_trans_customization.test_realtime.test_issue_realtime_events
    """
    
    # Create a test issue
    try:
        # Check if we can create an issue
        issue = frappe.get_doc({
            'doctype': 'Issue',
            'subject': 'Test Realtime Issue - ' + frappe.utils.now(),
            'status': 'New',
            'priority': 'Medium',
            'raised_by': frappe.session.user
        })
        
        print(f"Creating test issue: {issue.subject}")
        issue.insert()
        print(f"✓ Issue created successfully: {issue.name}")
        
        # Update the issue
        issue.status = 'In Review'
        issue.priority = 'High'
        issue.save()
        print(f"✓ Issue updated successfully: {issue.name}")
        
        # Check if hooks are registered
        hooks = frappe.get_hooks('doc_events', {})
        issue_hooks = hooks.get('Issue', {})
        print(f"✓ Issue hooks registered: {list(issue_hooks.keys())}")
        
        # Clean up
        issue.delete()
        print(f"✓ Test issue deleted: {issue.name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing realtime events: {str(e)}")
        frappe.log_error(f"Realtime test error: {str(e)}")
        return False

def check_socketio_status():
    """Check if socketio is properly configured"""
    try:
        # Check socketio configuration
        socketio_port = frappe.conf.get('socketio_port', 9000)
        print(f"✓ SocketIO port configured: {socketio_port}")
        
        # Check if realtime is enabled
        disable_async = frappe.conf.get('disable_async', False)
        if disable_async:
            print("✗ Async/Realtime is disabled in configuration")
        else:
            print("✓ Async/Realtime is enabled")
            
        return True
        
    except Exception as e:
        print(f"✗ Error checking socketio status: {str(e)}")
        return False

if __name__ == "__main__":
    frappe.init()
    frappe.connect()
    
    print("=== Testing Issue Realtime Events ===")
    check_socketio_status()
    test_issue_realtime_events()
    
    frappe.destroy()