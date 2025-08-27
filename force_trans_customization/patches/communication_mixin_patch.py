# Patch to add in_reply_to field to sendmail_input_dict in Communication mixin
import frappe
from frappe.core.doctype.communication.mixins import CommunicationEmailMixin

# Store the original method
_original_sendmail_input_dict = CommunicationEmailMixin.sendmail_input_dict

def patched_sendmail_input_dict(
    self,
    print_html=None,
    print_format=None,
    send_me_a_copy=None,
    print_letterhead=None,
    is_inbound_mail_communcation=None,
    print_language=None,
) -> dict:
    """Patched sendmail_input_dict to include in_reply_to field"""
    
    # Get the original dictionary
    result = _original_sendmail_input_dict(
        self,
        print_html=print_html,
        print_format=print_format,
        send_me_a_copy=send_me_a_copy,
        print_letterhead=print_letterhead,
        is_inbound_mail_communcation=is_inbound_mail_communcation,
        print_language=print_language,
    )
    
    # Add in_reply_to field if it exists
    if hasattr(self, 'in_reply_to') and self.in_reply_to:
        # Get the parent communication to extract its message_id
        try:
            parent_comm = frappe.get_doc("Communication", self.in_reply_to)
            if parent_comm.message_id:
                message_id_with_brackets = "<"+parent_comm.message_id+">"
                result["in_reply_to"] = message_id_with_brackets
                
                
                frappe.log(f"Added in_reply_to and References header to sendmail dict: {parent_comm.message_id}")
        except frappe.DoesNotExistError:
            frappe.log(f"Parent communication {self.in_reply_to} not found for in_reply_to")
    
    return result

def execute():
    """Apply the patch to Communication mixin"""
    # Apply the monkey patch
    CommunicationEmailMixin.sendmail_input_dict = patched_sendmail_input_dict
    #frappe.log("Applied Communication mixin patch for in_reply_to support")

# Auto-execute the patch when this module is imported
execute()