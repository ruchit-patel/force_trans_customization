import frappe

@frappe.whitelist()
def get_current_user_role_profile():
    """Get current user's role profile information"""
    try:
        role_profile = frappe.db.get_value("User", frappe.session.user, "role_profile_name")
        
        return {
            "role_profile_name": role_profile,
        }
    except Exception as e:
        frappe.log_error(f"Error getting user role profile: {str(e)}", "Role Profile Error")
        return {
            "role_profile_name": None,
        }