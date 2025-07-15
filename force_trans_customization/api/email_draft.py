import frappe
from frappe import _
from frappe.utils import now_datetime, get_formatted_email
import json

@frappe.whitelist()
def save_draft(**kwargs):
    """Save email as draft communication"""
    
    try:
        draft_name = kwargs.get("draft_name")
        
        if draft_name:
            # Update existing draft
            draft = frappe.get_doc("Communication", draft_name)
            # Validate permissions
            # if draft.owner != frappe.session.user:
            #     frappe.throw(_("You can only edit your own drafts"))
        else:
            # Check if draft already exists for this user and document
            existing_draft = frappe.db.get_value(
                "Communication",
                {
                    "reference_doctype": kwargs.get("doctype"),
                    "reference_name": kwargs.get("docname"),
                    "status": "Draft",
                    "owner": frappe.session.user,
                    "communication_medium": "Email"
                }
            )
            
            if existing_draft:
                # Update existing draft
                draft = frappe.get_doc("Communication", existing_draft)
            else:
                # Create new draft
                draft = frappe.new_doc("Communication")
                draft.reference_doctype = kwargs.get("doctype")
                draft.reference_name = kwargs.get("docname")
                draft.status = "Draft"
                draft.delivery_status = "Draft"
                draft.communication_type = "Communication"
                draft.communication_medium = "Email"
                draft.sent_or_received = "Sent"
                draft.communication_date = now_datetime()
        
        # Update draft content
        draft.subject = kwargs.get("subject") or "Draft Email"
        draft.content = kwargs.get("content") or ""
        draft.recipients = kwargs.get("recipients") or ""
        draft.cc = kwargs.get("cc") or ""
        draft.bcc = kwargs.get("bcc") or ""
        draft.sender = kwargs.get("sender") or get_formatted_email(frappe.session.user)
        draft.email_template = kwargs.get("email_template") or ""
        draft.delivery_status = "Draft"
        
        # Set text content for search
        if draft.content:
            draft.text_content = frappe.utils.strip_html_tags(draft.content)
        
        draft.save(ignore_permissions=True)
        
        return {
            "success": True,
            "draft_name": draft.name,
            "message": _("Draft saved successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving draft: {str(e)}", "Email Draft Error")
        return {
            "success": False,
            "message": _("Error saving draft: {0}").format(str(e))
        }

@frappe.whitelist()
def get_drafts(doctype, docname):
    """Get draft communications for a document"""
    
    try:
        drafts = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": doctype,
                "reference_name": docname,
                "status": "Draft",
                "communication_medium": "Email"
            },
            fields=["name", "subject", "content", "recipients", "cc", "bcc", "sender", "email_template", "modified"],
            order_by="modified desc"
        )
        
        return drafts
        
    except Exception as e:
        frappe.log_error(f"Error getting drafts: {str(e)}", "Email Draft Error")
        return []

@frappe.whitelist()
def send_draft(draft_name, form_values=None, selected_attachments=None):
    """Send a draft communication"""
    
    try:
        draft = frappe.get_doc("Communication", draft_name)
        
        # # Validate permissions
        # if draft.owner != frappe.session.user:
        #     frappe.throw(_("You can only send your own drafts"))
        
        # Update the draft with latest form values if provided
        if form_values:
            # Parse form_values if it's a JSON string
            if isinstance(form_values, str):
                form_values = json.loads(form_values)
            
            draft.subject = form_values.get("subject") or draft.subject
            draft.content = form_values.get("content") or draft.content
            draft.recipients = form_values.get("recipients") or draft.recipients
            draft.cc = form_values.get("cc") or draft.cc
            draft.bcc = form_values.get("bcc") or draft.bcc
            draft.sender = form_values.get("sender") or draft.sender
            draft.email_template = form_values.get("email_template") or draft.email_template
            draft.send_after = form_values.get("send_after") or draft.send_after
            # Set text content for search
            if draft.content:
                draft.text_content = frappe.utils.strip_html_tags(draft.content)
        
        # Update status to Linked
        draft.status = "Linked"
        draft.delivery_status = ""
        draft.save()
        
        # Send the email using the existing draft document
        # The send_email method will handle the delivery status properly
        draft.send_email()
        
        return {
            "success": True,
            "message": _("Draft sent successfully"),
            "communication_name": draft.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error sending draft: {str(e)}", "Email Draft Error")
        return {
            "success": False,
            "message": _("Error sending draft: {0}").format(str(e))
        }

@frappe.whitelist()
def delete_draft(draft_name):
    """Delete a draft communication"""
    
    try:
        draft = frappe.get_doc("Communication", draft_name)
        
        # Validate permissions
        if draft.owner != frappe.session.user:
            frappe.throw(_("You can only delete your own drafts"))
        
        # Delete the draft
        draft.delete()
        
        return {
            "success": True,
            "message": _("Draft deleted successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Error deleting draft: {str(e)}", "Email Draft Error")
        return {
            "success": False,
            "message": _("Error deleting draft: {0}").format(str(e))
        }

@frappe.whitelist()
def undo_scheduled_email(communication_name):
    """Cancel a scheduled email and revert to draft status"""
    
    try:
        # Get the communication document
        communication = frappe.get_doc("Communication", communication_name)
        
        # Check if this is a scheduled email (has send_after set)
        if not communication.send_after:
            return {
                "success": False,
                "message": _("This email is not scheduled for delayed sending")
            }
        
        # Check if the email has already been sent
        if communication.delivery_status in ["Sent", "Delivered"]:
            return {
                "success": False,
                "message": _("This email has already been sent and cannot be undone")
            }
        
        # Find and delete the email queue entry
        email_queue_entries = frappe.get_all(
            "Email Queue",
            filters={
                "communication": communication_name,
                "status": ["in", ["Not Sent", "Partially Sent"]]
            },
            fields=["name"]
        )
        
        for queue_entry in email_queue_entries:
            try:
                frappe.delete_doc("Email Queue", queue_entry.name, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error deleting email queue entry {queue_entry.name}: {str(e)}")
        
        # Update communication status back to Draft
        communication.status = "Draft"
        communication.delivery_status = "Draft"
        communication.send_after = None
        communication.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": _("Email sending cancelled successfully"),
            "communication_name": communication.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error undoing scheduled email: {str(e)}", "Email Undo Error")
        return {
            "success": False,
            "message": _("Error cancelling email: {0}").format(str(e))
        }

@frappe.whitelist()
def get_scheduled_emails(doctype=None, docname=None):
    """Get scheduled emails for a document or user"""
    
    try:
        filters = {
            "send_after": ["is", "set"],
            "delivery_status": ["not in", ["Sent", "Delivered"]],
            "communication_medium": "Email"
        }
        
        if doctype and docname:
            filters["reference_doctype"] = doctype
            filters["reference_name"] = docname
        else:
            # Get emails scheduled by current user
            filters["owner"] = frappe.session.user
        
        scheduled_emails = frappe.get_all(
            "Communication",
            filters=filters,
            fields=["name", "subject", "recipients", "send_after", "delivery_status", "modified"],
            order_by="send_after asc"
        )
        
        return scheduled_emails
        
    except Exception as e:
        frappe.log_error(f"Error getting scheduled emails: {str(e)}", "Email Undo Error")
        return []

@frappe.whitelist()
def get_recent_communication(doctype, docname, minutes=2):
    """Get the most recent communication created by current user for a document within specified minutes"""
    
    try:
        from frappe.utils import now_datetime
        from datetime import timedelta
        
        # Convert minutes to integer if it's a string
        minutes = int(minutes) if isinstance(minutes, str) else minutes
        
        # Calculate time threshold (default 2 minutes ago)
        time_threshold = now_datetime() - timedelta(minutes=minutes)
        
        communications = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": doctype,
                "reference_name": docname,
                "owner": frappe.session.user,
                "communication_medium": "Email",
                "send_after": ["is", "set"],
                "creation": [">=", time_threshold]
            },
            fields=["name", "send_after", "creation"],
            order_by="creation desc",
            limit=1
        )
        
        if communications:
            return communications[0]
        else:
            return None
            
    except Exception as e:
        frappe.log_error(f"Error getting recent communication: {str(e)}", "Email Undo Error")
        return None

