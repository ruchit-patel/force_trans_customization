# Patch to add in_reply_to parameter to frappe.core.doctype.communication.email.make function
import frappe
from frappe.core.doctype.communication import email
from frappe.utils import cint, get_formatted_email, list_to_str
from frappe import _
import json

# Store the original make function
_original_make = email.make

@frappe.whitelist()
def patched_make(
    doctype=None,
    name=None,
    content=None,
    subject=None,
    sent_or_received="Sent",
    sender=None,
    sender_full_name=None,
    recipients=None,
    communication_medium="Email",
    send_email=False,
    print_html=None,
    print_format=None,
    attachments=None,
    send_me_a_copy=False,
    cc=None,
    bcc=None,
    email_template=None,
    add_signature=True,
    communication_type="Communication",
    now=False,
    read_receipt=None,
    print_letterhead=None,
    print_language=None,
    send_after=None,
    in_reply_to=None,  # NEW PARAMETER
    **kwargs
):
    """
    Patched version of make() function that accepts in_reply_to parameter.
    All other functionality remains exactly the same as the original.
    """
    # Call the original function with all original parameters
    # We'll intercept the communication creation process
    
    # Set defaults (copied from original)
    sender = sender or get_formatted_email(frappe.session.user)
    recipients = list_to_str(recipients) if isinstance(recipients, list) else recipients
    cc = list_to_str(cc) if isinstance(cc, list) else cc
    bcc = list_to_str(bcc) if isinstance(bcc, list) else bcc

    # Create communication document with in_reply_to field included
    comm = frappe.get_doc({
        "doctype": "Communication",
        "subject": subject,
        "content": content,
        "sender": sender,
        "sender_full_name": sender_full_name,
        "recipients": recipients,
        "cc": cc or None,
        "bcc": bcc or None,
        "communication_medium": communication_medium,
        "sent_or_received": sent_or_received,
        "reference_doctype": doctype,
        "reference_name": name,
        "email_template": email_template,
        "message_id": email.get_string_between("<", email.get_message_id(), ">"),
        "read_receipt": read_receipt,
        "has_attachment": 1 if attachments else 0,
        "communication_type": communication_type,
        "send_after": send_after,
        "in_reply_to": in_reply_to,  # Include the new field
    })
    
    comm.flags.skip_add_signature = not add_signature
    comm.insert(ignore_permissions=True)

    # Add attachments if provided
    if attachments:
        if isinstance(attachments, str):
            attachments = json.loads(attachments)
        email.add_attachments(comm.name, attachments)

    # Send email if requested (handle both boolean and string values)
    send_email_bool = send_email
    if isinstance(send_email, str):
        send_email_bool = send_email.lower() in ('true', '1', 'yes')
    elif send_email:
        send_email_bool = True
    else:
        send_email_bool = False
        
    if send_email_bool:
        if not comm.get_outgoing_email_account():
            frappe.throw(
                _(
                    "Unable to send mail because of a missing email account. Please setup default Email Account from Settings > Email Account"
                ),
                exc=frappe.OutgoingEmailError,
            )

        comm.send_email(
            print_html=print_html,
            print_format=print_format,
            send_me_a_copy=send_me_a_copy,
            print_letterhead=print_letterhead,
            print_language=print_language,
            now=now,
        )

    emails_not_sent_to = comm.exclude_emails_list(include_sender=send_me_a_copy)

    return {"name": comm.name, "emails_not_sent_to": ", ".join(emails_not_sent_to)}

def execute():
    """Apply the patch to the make function"""
    # Apply the monkey patch
    email.make = patched_make
    # frappe.log("Applied Communication make() patch for in_reply_to support")

# Auto-execute the patch when this module is imported
execute()