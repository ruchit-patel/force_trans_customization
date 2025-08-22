import frappe

def modify_email_headers(email_obj):
    """
    Hook function to modify email headers before sending
    This is called by the 'make_email_body_message' hook
    """
    try:
        # Set Reply-To to as blank
        email_obj.set_header("Reply-To", '')
        
        # Add References header if In-Reply-To is present
        try:
            if hasattr(email_obj, 'msg_root') and hasattr(email_obj.msg_root, '_headers'):
                headers = email_obj.msg_root._headers
                # Search through the headers list to find In-Reply-To
                for header in headers:
                    if header[0] == "In-Reply-To":  # header is a tuple (name, value)
                        in_reply_to = header[1]
                        # Set References to the same value as In-Reply-To for better email threading
                        email_obj.set_header("References", in_reply_to)
                        frappe.log(f"Set References header to: {in_reply_to}")
                        break
        except Exception as e:
            frappe.log_error(f"Error setting References header: {str(e)}")
        
        frappe.log(f"Set Reply-To to team email: blank")
    except Exception as e:
        frappe.log_error(
            message=f"Error modifying email headers: {str(e)}",
            title="Email Header Modification Error"
        )