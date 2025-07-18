import frappe

def modify_email_headers(email_obj):
    """
    Hook function to modify email headers before sending
    This is called by the 'make_email_body_message' hook
    """
    try:
        # Get the email account used for sending
        email_account = email_obj.email_account
        if email_account and email_account.email_id:
            # Set Reply-To to team email
            team_email = email_account.email_id
            email_obj.set_header("Reply-To", team_email)
            frappe.log(f"Set Reply-To to team email: {team_email}")
    except Exception as e:
        frappe.log_error(
            message=f"Error modifying email headers: {str(e)}",
            title="Email Header Modification Error"
        )