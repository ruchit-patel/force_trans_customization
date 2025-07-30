import frappe
from frappe import _
import json

@frappe.whitelist()
def test_realtime_emission():
    """Test function to emit realtime events manually"""
    try:
        # Emit a test list_update event
        frappe.publish_realtime(
            event='list_update',
            message={
                'doctype': 'Issue',
                'name': 'TEST-ISSUE-001',
                'action': 'test',
                'modified_by': frappe.session.user,
                'modified': frappe.utils.now(),
                'test': True
            },
            user=None
        )
        
        # Also emit Issue-specific events
        frappe.publish_realtime(
            event='Issue_update',
            message={
                'doctype': 'Issue',
                'name': 'TEST-ISSUE-001',
                'subject': 'Test Issue for Realtime',
                'status': 'New',
                'priority': 'Medium',
                'test': True
            },
            user=None
        )
        
        frappe.logger().info("Test realtime events emitted successfully")
        
        return {
            'success': True,
            'message': 'Test realtime events emitted successfully'
        }
        
    except Exception as e:
        frappe.logger().error(f"Failed to emit test realtime events: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

@frappe.whitelist()
def create_test_issue():
    """Create a test issue to trigger realtime events"""
    try:
        issue = frappe.get_doc({
            'doctype': 'Issue',
            'subject': f'Test Realtime Issue - {frappe.utils.now()}',
            'status': 'New',
            'priority': 'Medium',
            'raised_by': frappe.session.user,
            'description': 'This is a test issue created to verify realtime updates'
        })
        
        issue.insert()
        frappe.db.commit()
        
        return {
            'success': True,
            'issue_name': issue.name,
            'message': f'Test issue created: {issue.name}'
        }
        
    except Exception as e:
        frappe.logger().error(f"Failed to create test issue: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

@frappe.whitelist()
def update_test_issue(issue_name):
    """Update a test issue to trigger realtime events"""
    try:
        issue = frappe.get_doc('Issue', issue_name)
        issue.status = 'In Review'
        issue.priority = 'High'
        issue.add_comment('Comment', 'Updated via realtime test')
        issue.save()
        frappe.db.commit()
        
        return {
            'success': True,
            'message': f'Test issue updated: {issue_name}'
        }
        
    except Exception as e:
        frappe.logger().error(f"Failed to update test issue: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

@frappe.whitelist()
def delete_test_issue(issue_name):
    """Delete a test issue to trigger realtime events"""
    try:
        issue = frappe.get_doc('Issue', issue_name)
        issue.delete()
        frappe.db.commit()
        
        return {
            'success': True,
            'message': f'Test issue deleted: {issue_name}'
        }
        
    except Exception as e:
        frappe.logger().error(f"Failed to delete test issue: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }