import frappe

def modify_email_headers(email_obj):
    """
    Hook function to modify email headers before sending
    This is called by the 'make_email_body_message' hook
    """
    try:
        # Set Reply-To to as blank
        email_obj.set_header("Reply-To", '')
        frappe.log(f"Set Reply-To to team email: blank")
    except Exception as e:
        frappe.log_error(
            message=f"Error modifying email headers: {str(e)}",
            title="Email Header Modification Error"
        )