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
            if draft.owner != frappe.session.user:
                frappe.throw(_("You can only edit your own drafts"))
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

    """Send a draft communication"""
    
    try:
        draft = frappe.get_doc("Communication", draft_name)
        
        # Validate permissions
        if draft.owner != frappe.session.user:
            frappe.throw(_("You can only send your own drafts"))
        
        # Change status from Draft to Linked
        draft.status = "Linked"
        draft.save()
        
        # Send the email using Frappe's email system
        from frappe.core.doctype.communication.email import make
        
        result = make(
            doctype=draft.reference_doctype,
            name=draft.reference_name,
            content=draft.content,
            subject=draft.subject,
            recipients=draft.recipients,
            cc=draft.cc,
            bcc=draft.bcc,
            sender=draft.sender,
            send_email=True
        )
        
        return {
            "success": True,
            "message": _("Draft sent successfully"),
            "communication_name": result.get("name")
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
