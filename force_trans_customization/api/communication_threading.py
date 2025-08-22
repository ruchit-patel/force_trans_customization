# API for handling communication threading
import frappe
from frappe.core.doctype.communication.email import make
from frappe import _

@frappe.whitelist()
def create_reply_communication(**kwargs):
    """
    Create a communication with proper reply threading
    
    Args:
        reply_to_communication: Name of the communication this is replying to
        Other args: Same as frappe.core.doctype.communication.email.make
    """
    try:
        # Extract required arguments
        reference_doctype = kwargs.get("reference_doctype")
        reference_name = kwargs.get("reference_name")
        recipients = kwargs.get("recipients")
        sender = kwargs.get("sender")
        subject = kwargs.get("subject")
        content = kwargs.get("content")
        reply_to_communication = kwargs.get("reply_to_communication")
        
        # Extract optional arguments
        cc = kwargs.get("cc")
        bcc = kwargs.get("bcc")
        send_email = kwargs.get("send_email", True)
        email_template = kwargs.get("email_template")
        attachments = kwargs.get("attachments")
        send_me_a_copy = kwargs.get("send_me_a_copy")
        print_html = kwargs.get("print_html")
        print_format = kwargs.get("print_format")
        send_after = kwargs.get("send_after")
        
        # Use the patched make() function that supports in_reply_to parameter
        comm = make(
            doctype=reference_doctype,
            name=reference_name,
            recipients=recipients,
            sender=sender,
            subject=subject,
            content=content,
            send_email=send_email,
            cc=cc,
            bcc=bcc,
            email_template=email_template,
            attachments=attachments,
            send_me_a_copy=send_me_a_copy,
            print_html=print_html,
            print_format=print_format,
            send_after=send_after,
            in_reply_to=reply_to_communication  # Use the new parameter
        )
        
        comm_name = comm.get("name")
        
        return {
            "name": comm_name,
            "success": True
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating reply communication: {str(e)}", "Communication Threading Error")
        return {
            "success": False,
            "message": _("Error creating communication: {0}").format(str(e))
        }
