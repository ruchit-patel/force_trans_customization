import frappe
from frappe import _


def emit_issue_update(doc, method):
    """Emit socket event when Issue is updated"""
    try:
        # Use Frappe's built-in socket emission
        frappe.publish_realtime(
            event='doctype_update',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'modified_by': doc.modified_by,
                'modified': doc.modified,
                'subject': doc.subject,
                'status': doc.status,
                'priority': doc.priority
            },
            user=None  # Broadcast to all users, or specify specific users
        )
        
        # Also emit a more specific Issue event
        frappe.publish_realtime(
            event='Issue_update',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'modified_by': doc.modified_by,
                'modified': doc.modified,
                'subject': doc.subject,
                'status': doc.status,
                'priority': doc.priority,
                'assigned_to': getattr(doc, 'assigned_to', None)
            },
            user=None
        )
        
        frappe.logger().info(f"Socket event emitted for Issue update: {doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to emit socket event for Issue {doc.name}: {str(e)}")


def emit_issue_create(doc, method):
    """Emit socket event when Issue is created"""
    try:
        frappe.publish_realtime(
            event='doc_create',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'owner': doc.owner,
                'created': doc.creation,
                'subject': doc.subject,
                'status': doc.status,
                'priority': doc.priority
            },
            user=None
        )
        
        frappe.publish_realtime(
            event='Issue_create',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'owner': doc.owner,
                'created': doc.creation,
                'subject': doc.subject,
                'status': doc.status,
                'priority': doc.priority
            },
            user=None
        )
        
        frappe.logger().info(f"Socket event emitted for Issue creation: {doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to emit socket event for Issue creation {doc.name}: {str(e)}")


def emit_issue_delete(doc, method):
    """Emit socket event when Issue is deleted"""
    try:
        frappe.publish_realtime(
            event='doc_delete',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'subject': doc.subject
            },
            user=None
        )
        
        frappe.publish_realtime(
            event='Issue_delete',
            message={
                'doctype': 'Issue', 
                'name': doc.name,
                'subject': doc.subject
            },
            user=None
        )
        
        frappe.logger().info(f"Socket event emitted for Issue deletion: {doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to emit socket event for Issue deletion {doc.name}: {str(e)}")


def on_issue_save(doc, method):
    """
    Called after an Issue document is saved (covers both insert and update)
    """
    # Check if this is an update (not an insert)
    if not doc.is_new():
        emit_issue_update(doc, method)


def on_issue_insert(doc, method):
    """
    Called after an Issue document is inserted
    """
    emit_issue_create(doc, method)


def on_issue_cancel(doc, method):
    """
    Called when an Issue document is cancelled
    """
    try:
        frappe.publish_realtime(
            event='doctype_update',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'modified_by': frappe.session.user,
                'status': 'Cancelled',
                'subject': doc.subject
            },
            user=None
        )
        
        frappe.logger().info(f"Socket event emitted for Issue cancellation: {doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to emit socket event for Issue cancellation {doc.name}: {str(e)}")