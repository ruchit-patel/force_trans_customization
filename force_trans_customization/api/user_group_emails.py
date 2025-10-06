import frappe
from frappe import _


@frappe.whitelist()
def get_user_associated_emails():
    """
    Get all associated emails from User Groups where the current user is a member.

    Returns:
        list: List of unique associated email addresses
    """
    current_user = frappe.session.user

    # Get all User Groups
    user_groups = frappe.get_all(
        "User Group",
        fields=["name", "custom_associated_email"]
    )

    associated_emails = []

    for group in user_groups:
        # Skip if no associated email
        if not group.get("custom_associated_email"):
            continue

        # Get the full User Group document to access the members child table
        user_group_doc = frappe.get_doc("User Group", group.name)

        # Check if current user is in the members list
        is_member = False
        for member in user_group_doc.user_group_members:
            if member.user == current_user:
                is_member = True
                break

        # If user is a member, add the associated email
        if is_member:
            associated_emails.append(group.custom_associated_email)

    # Remove duplicates and return
    unique_emails = list(set(associated_emails))

    # Always include the user's own email as fallback
    user_doc = frappe.get_doc("User", current_user)
    if user_doc.email and user_doc.email not in unique_emails:
        unique_emails.insert(0, user_doc.email)

    return unique_emails
