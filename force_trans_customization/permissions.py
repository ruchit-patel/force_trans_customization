"""
Permissions Module for Force Trans Custom App

This module contains permission query functions that restrict data access based on user roles and role profiles.

IMPORTANT SETUP REQUIREMENTS:
1. Ensure you have the 'custom_assigned_csm_team' field added to the Issue doctype
2. Ensure you have the 'custom_users_assigned' Table MultiSelect field added to the Issue doctype (uses Team User Assignment child table)
3. Create User Groups in the system (User Group doctype) 
4. Assign users to appropriate User Groups via the User Group Member child table
5. Assign appropriate roles to users (CSM, Customer Success Manager, etc.)
6. Create Role Profiles (like "Tracking Team", "Accounting Team") and assign them to users

CONFIGURATION:
To use these permission functions, you need to add them to your doctype's permission hooks.
In your Issue doctype's hooks.py or in a custom app's hooks.py, add:

permission_query_conditions = {
    "Issue": "force_trans_custom.permissions.issue_query"
}

has_permission = {
    "Issue": "force_trans_custom.permissions.issue_has_permission"
}

ROLE CUSTOMIZATION:
Modify the 'csm_roles', 'tracking_role_profile', and 'accounting_role_profile' to match your actual role names and role profiles.

HOW IT WORKS:

QUERY-LEVEL PERMISSIONS (issue_query):
- Controls what Issues appear in lists/reports
- SHARED DOCUMENTS: Issues shared with a user (via Share button) appear in their list regardless of restrictions
- If a user has any of the defined Support Team roles, they will see Issues where:
  - The Issue's custom_assigned_csm_team field matches their assigned User Group(s), OR
  - The user is individually assigned to the Issue via custom_users_assigned table, OR
  - The Issue has been explicitly shared with them
- If a user has "Tracking Team" role profile, they will see Issues where:
  - The Issue status is NOT "New", "In Review",  OR
  - The Issue has been explicitly shared with them
- If a user has "Accounting Team" role profile, they will see Issues where:
  - The Issue status is "Delivered" or "Closed", OR
  - The Issue has been explicitly shared with them
- If a user belongs to multiple User Groups, they'll see Issues from all their groups
- Users without restricted roles/profiles see all Issues (no restriction)

DOCUMENT-LEVEL PERMISSIONS (issue_has_permission):
- Controls access to individual Issue documents
- SHARED DOCUMENTS: If an Issue is shared with a user (via Share button), they get access regardless of restrictions
- If a user has any of the defined Support Team roles:
  - They can access Issues where custom_assigned_csm_team matches their assigned User Group(s), OR
  - They are individually assigned to the Issue via custom_users_assigned table
  - They get "Permission Denied" for Issues outside their groups and not individually assigned (unless shared)
- If a user has "Tracking Team" role profile:
  - They cannot access Issues with status "New", "In Review"
  - They get "Permission Denied" for Issues with these statuses (unless shared)
- If a user has "Accounting Team" role profile:
  - They can only access Issues with status "Delivered" or "Closed"
  - They get "Permission Denied" for Issues with other statuses (unless shared)
- Users without restricted roles/profiles can access all Issues

FAIL-SAFE BEHAVIOR:
- If there's an error in either function, the system fails safely (allows access)
"""

import frappe
import frappe.share

def issue_query(user):
    """Restrict Issue list for team members based on their roles and role profiles."""
    # Define CSM team roles - adjust these role names based on your actual role setup
    csm_roles = ["Support Team"]
    # Define role profiles for different teams
    tracking_role_profile = "Tracking Team"
    accounting_role_profile = "Accounting Team"
    
    try:
        # Get user document to check role profile
        user_doc = frappe.get_doc("User", user)
        user_role_profile = user_doc.get("role_profile_name")
        
        # Check if user has Accounting Team role profile
        if user_role_profile == accounting_role_profile:
            # Get shared documents for this user
            shared_issues = frappe.share.get_shared("Issue", user, rights=["read"])
            
            # Build the query condition for Accounting Team role profile
            conditions = []
            
            # Add status condition - only allow Delivered and Closed
            allowed_statuses = ["Delivered", "Closed"]
            status_conditions = "', '".join(allowed_statuses)
            conditions.append(f"`tabIssue`.status IN ('{status_conditions}')")
            
            # Add shared documents condition if any documents are shared
            if shared_issues:
                shared_conditions = "', '".join(shared_issues)
                conditions.append(f"`tabIssue`.name IN ('{shared_conditions}')")
            
            # Combine conditions with OR
            return f"({' OR '.join(conditions)})"
        
        # Check if user has Tracking Team role profile
        elif user_role_profile == tracking_role_profile:
            # Get shared documents for this user
            shared_issues = frappe.share.get_shared("Issue", user, rights=["read"])
            
            # Build the query condition for Tracking Team role profile
            conditions = []
            
            # Add status condition - exclude New, In Review
            restricted_statuses = ["New", "In Review"]
            status_conditions = "', '".join(restricted_statuses)
            conditions.append(f"`tabIssue`.status NOT IN ('{status_conditions}')")
            
            # Add shared documents condition if any documents are shared
            if shared_issues:
                shared_conditions = "', '".join(shared_issues)
                conditions.append(f"`tabIssue`.name IN ('{shared_conditions}')")
            
            # Combine conditions with OR
            return f"({' OR '.join(conditions)})"
        
        # Get user roles for CSM team check
        user_roles = frappe.get_roles(user)
        
        # Check if user has any CSM role
        if any(role in user_roles for role in csm_roles):
            # Find which user groups this user belongs to
            user_groups = frappe.get_all(
                "User Group Member",
                filters={"user": user},
                fields=["parent"],
                pluck="parent"
            )
            
            # Get shared documents for this user
            shared_issues = frappe.share.get_shared("Issue", user, rights=["read"])
            
            # Build the query condition
            conditions = []
            
            # Add user group condition if user belongs to any groups
            if user_groups:
                if len(user_groups) == 1:
                    conditions.append(f"`tabIssue`.custom_assigned_csm_team = '{user_groups[0]}'")
                else:
                    user_group_conditions = "', '".join(user_groups)
                    conditions.append(f"`tabIssue`.custom_assigned_csm_team IN ('{user_group_conditions}')")
            
            # Add condition for individually assigned users (custom_users_assigned table)
            # This allows users to see issues they're individually assigned to via the new assignment system
            conditions.append(f"""EXISTS (
                SELECT 1 FROM `tabTeam User Assignment` 
                WHERE `tabTeam User Assignment`.parent = `tabIssue`.name 
                AND `tabTeam User Assignment`.parenttype = 'Issue'
                AND `tabTeam User Assignment`.parentfield = 'custom_users_assigned'
                AND `tabTeam User Assignment`.user_assigned = '{user}'
            )""")
            
            # Add shared documents condition if any documents are shared
            if shared_issues:
                shared_conditions = "', '".join(shared_issues)
                conditions.append(f"`tabIssue`.name IN ('{shared_conditions}')")
            
            # Combine conditions with OR
            if conditions:
                return f"({' OR '.join(conditions)})"
            else:
                # CSM user with no groups and no shared docs - fallback to individual assignment check
                return f"""EXISTS (
                    SELECT 1 FROM `tabTeam User Assignment` 
                    WHERE `tabTeam User Assignment`.parent = `tabIssue`.name 
                    AND `tabTeam User Assignment`.parenttype = 'Issue'
                    AND `tabTeam User Assignment`.parentfield = 'custom_users_assigned'
                    AND `tabTeam User Assignment`.user_assigned = '{user}'
                )"""
    except Exception as e:
        # Log error and allow access if there's an issue (fail-safe approach)
        frappe.log_error(f"Error in issue_query permission function: {str(e)}", "Permissions Error")
    
    return ""  # No restriction for other roles/profiles or if error occurs

def issue_has_permission(doc, user):
    """Check if user has permission to access the Issue."""
    # Define CSM team roles - should match the roles in issue_query function
    csm_roles = ["Support Team"]
    # Define role profiles for different teams
    tracking_role_profile = "Tracking Team"
    accounting_role_profile = "Accounting Team"
    
    try:
        # First check if the document is explicitly shared with this user
        # This allows special access overrides through Frappe's built-in sharing
        if frappe.share.get_shared("Issue", user, filters=[["share_name", "=", doc.name]]):
            return True
        
        # Get user document to check role profile
        user_doc = frappe.get_doc("User", user)
        user_role_profile = user_doc.get("role_profile_name")
        
        # Check if user has Accounting Team role profile
        if user_role_profile == accounting_role_profile:
            # Check if the document status is in allowed statuses
            doc_status = doc.get("status")
            allowed_statuses = ["Delivered", "Closed"]
            if doc_status in allowed_statuses:
                return True
            else:
                # User doesn't have access to this Issue (not in allowed statuses)
                return False
        
        # Check if user has Tracking Team role profile
        elif user_role_profile == tracking_role_profile:
            # Check if the document status is NOT in restricted statuses
            doc_status = doc.get("status")
            restricted_statuses = ["New", "In Review"]
            if doc_status not in restricted_statuses:
                return True
            else:
                # User doesn't have access to this Issue (restricted status)
                return False
        
        # Get user roles for CSM team check
        user_roles = frappe.get_roles(user)
        
        # Check if user has any CSM role
        if any(role in user_roles for role in csm_roles):
            # Check if user is individually assigned to this issue via custom_users_assigned table
            individually_assigned = frappe.get_all(
                "Team User Assignment",
                filters={
                    "parent": doc.name,
                    "parenttype": "Issue",
                    "parentfield": "custom_users_assigned",
                    "user_assigned": user
                },
                limit=1
            )
            
            if individually_assigned:
                # User is individually assigned to this issue - grant access
                return True
            
            # Find which user groups this user belongs to
            user_groups = frappe.get_all(
                "User Group Member",
                filters={"user": user},
                fields=["parent"],
                pluck="parent"
            )
            
            if user_groups:
                # Check if the document's user group matches any of the user's groups
                doc_user_group = doc.get("custom_assigned_csm_team")
                if doc_user_group and doc_user_group in user_groups:
                    return True
                else:
                    # User doesn't have access to this specific Issue via team assignment
                    return False
            else:
                # CSM user is not assigned to any user group - check individual assignment only
                # (individual assignment was already checked above, so deny access here)
                return False
    except Exception as e:
        # Log error and allow access if there's an issue (fail-safe approach)
        frappe.log_error(f"Error in issue_has_permission function: {str(e)}", "Permissions Error")
        return True  # Fail-safe: allow access if error occurs
    
    # No restriction for other roles/profiles (non-restricted users)
    return True