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

    """
    Test function to verify that email header modification is working
    """
    try:
        # Create a test email object
        from frappe.email.email_body import get_email
        
        # Get a test email account
        email_account = frappe.db.get_value(
            "Email Account", 
            {"enable_outgoing": 1}, 
            "name"
        )
        
        if not email_account:
            return {"status": "error", "message": "No email account found"}
        
        email_account_doc = frappe.get_cached_doc("Email Account", email_account)
        
        # Create a test email
        test_email = get_email(
            recipients=["test@example.com"],
            sender=email_account_doc.email_id,
            subject="Test Email Header Modification",
            message="This is a test email to verify header modification",
            email_account=email_account_doc
        )
        
        # Call our hook function
        modify_email_headers(test_email)
        
        # Check if Reply-To header was set
        reply_to_header = test_email.msg_root.get("Reply-To")
        
        if reply_to_header:
            return {
                "status": "success", 
                "message": f"Reply-To header set to: {reply_to_header}",
                "team_email": email_account_doc.email_id
            }
        else:
            return {
                "status": "warning", 
                "message": "Reply-To header not set",
                "team_email": email_account_doc.email_id
            }
            
    except Exception as e:
        frappe.log_error(
            message=f"Error testing email header modification: {str(e)}",
            title="Email Header Test Error"
        )
        return {"status": "error", "message": str(e)}