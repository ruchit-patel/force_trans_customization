import frappe


def emit_list_update(doc, method, action=None):
    """
    Emit Frappe's standard list_update event for Issue documents.
    This follows the same pattern as Frappe's core list view updates.
    """
    try:
        # Determine action based on method if not provided
        if not action:
            action_map = {
                'after_insert': 'insert',
                'on_update': 'update', 
                'on_cancel': 'cancel',
                'on_trash': 'delete',
                'before_save': 'update'
            }
            action = action_map.get(method, 'update')

        # Print to console for debugging
        print(f"🔥 REALTIME DEBUG: Emitting list_update for Issue {action}: {doc.name}")

        # Emit the standard list_update event that Frappe's list views listen for
        frappe.publish_realtime(
            event='list_update',
            message={
                'doctype': 'Issue',
                'name': doc.name,
                'action': action,
                'modified_by': getattr(doc, 'modified_by', frappe.session.user),
                'modified': getattr(doc, 'modified', frappe.utils.now()),
            },
            # Send to all users who have access to Issue doctype
            user=None
        )
        
        # Also emit to console for immediate feedback
        print(f"🚀 REALTIME: list_update event emitted for Issue {action}: {doc.name}")
        frappe.logger().info(f"list_update event emitted for Issue {action}: {doc.name}")
        
    except Exception as e:
        print(f"❌ REALTIME ERROR: Failed to emit list_update event for Issue {doc.name}: {str(e)}")
        frappe.logger().error(f"Failed to emit list_update event for Issue {doc.name}: {str(e)}")


def on_issue_insert(doc, method):
    """Called after an Issue document is inserted"""
    emit_list_update(doc, method, 'insert')


def on_issue_save(doc, method):
    """Called after an Issue document is saved (update only, not insert)"""
    if not doc.is_new():
        emit_list_update(doc, method, 'update')


def on_issue_cancel(doc, method):
    """Called when an Issue document is cancelled"""
    emit_list_update(doc, method, 'cancel')


def on_issue_trash(doc, method):
    """Called when an Issue document is deleted"""
    emit_list_update(doc, method, 'delete')