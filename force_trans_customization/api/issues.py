import frappe
from frappe import _


@frappe.whitelist()
def get_issues_with_assignments(limit_page_length=10, limit_start=0, filters=None, order_by="creation desc"):
    """
    Get issues list with custom_users_assigned child table data
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Handle filters
        if filters is None:
            filters = {}
        elif isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        # Base fields to fetch from Issue doctype
        fields = [
            "name",
            "subject", 
            "status",
            "priority",
            "raised_by",
            "customer",
            "project",
            "issue_type",
            "creation",
            "modified",
            "owner",
            "description"
        ]
        
        # Process filters to handle special cases
        processed_filters = {}
        or_filters = []
        
        for key, value in filters.items():
            if key == 'subject':
                # Special handling for subject - search in both subject and description
                if isinstance(value, list) and len(value) == 2 and value[0] == 'like':
                    # Create OR filter for subject field to search in both title and description
                    or_filters.extend([
                        ['subject', 'like', value[1]],
                        ['description', 'like', value[1]]
                    ])
                else:
                    # For equals, search only in subject
                    processed_filters['subject'] = value
            else:
                processed_filters[key] = value
        
        # Get issues using frappe.get_list
        if or_filters:
            # Use or_filters when we have subject search
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters=processed_filters,
                or_filters=or_filters,
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start
            )
        else:
            # Normal filters only
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters=processed_filters,
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start
            )
        
        # For each issue, fetch the custom_users_assigned child table data and tags
        for issue in issues:
            # Get child table data for custom_users_assigned
            user_assignments = frappe.db.get_all(
                "Team User Assignment",
                filters={"parent": issue.name},
                fields=["*"],  # Get all fields to ensure user_assigned is included
                order_by="idx asc"  # Order by idx to maintain the order from the form
            )
            
            issue["custom_users_assigned"] = user_assignments
            
            # Get tags for this issue
            tags = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "document_name": issue.name
                },
                fields=["tag"],
                order_by="creation asc"
            )
            
            # Convert tags to a simple list of tag names
            issue["_user_tags"] = [tag.tag for tag in tags] if tags else []
        
        return issues
        
    except Exception as e:
        frappe.log_error(f"Error in get_issues_with_assignments: {str(e)}")
        frappe.throw(_("Failed to fetch issues with assignments: {0}").format(str(e)))


@frappe.whitelist()
def get_issues_count_with_filters(filters=None):
    """
    Get total count of issues with filters (for pagination)
    This function respects the same permission system as get_issues_with_assignments
    """
    try:
        # Handle filters
        if filters is None:
            filters = {}
        elif isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        # Process filters to handle special cases (same as main function)
        processed_filters = {}
        or_filters = []
        
        for key, value in filters.items():
            if key == 'subject':
                # Special handling for subject - search in both subject and description
                if isinstance(value, list) and len(value) == 2 and value[0] == 'like':
                    # Create OR filter for subject field to search in both title and description
                    or_filters.extend([
                        ['subject', 'like', value[1]],
                        ['description', 'like', value[1]]
                    ])
                else:
                    # For equals, search only in subject
                    processed_filters['subject'] = value
            else:
                processed_filters[key] = value
        
        # Use frappe.get_list with count=True to respect permissions
        if or_filters:
            # Use or_filters when we have subject search
            result = frappe.get_list(
                "Issue",
                filters=processed_filters,
                or_filters=or_filters,
                limit_page_length=0,  # Get all records
                as_list=True,
                ignore_permissions=False  # Explicitly respect permissions
            )
        else:
            # Normal filters only
            result = frappe.get_list(
                "Issue",
                filters=processed_filters,
                limit_page_length=0,  # Get all records
                as_list=True,
                ignore_permissions=False  # Explicitly respect permissions
            )
        
        # Return the count of records that the user is allowed to see
        return len(result)
        
    except Exception as e:
        frappe.log_error(f"Error in get_issues_count_with_filters: {str(e)}")
        frappe.throw(_("Failed to get issues count: {0}").format(str(e)))


@frappe.whitelist()
def get_single_issue_with_assignments(issue_name):
    """
    Get a single issue with custom_users_assigned child table data
    Used for realtime updates to refresh individual rows
    """
    try:
        # Base fields to fetch from Issue doctype
        fields = [
            "name",
            "subject", 
            "status",
            "priority",
            "raised_by",
            "customer",
            "project",
            "issue_type",
            "creation",
            "modified",
            "owner",
            "description"
        ]
        
        # Get the single issue
        issue = frappe.get_doc("Issue", issue_name)
        
        # Convert to dict with only required fields
        issue_data = {}
        for field in fields:
            issue_data[field] = getattr(issue, field, None)
        
        # Get child table data for custom_users_assigned
        user_assignments = frappe.db.get_all(
            "Team User Assignment",
            filters={"parent": issue_name},
            fields=["*"],  # Get all fields to ensure user_assigned is included
            order_by="idx asc"  # Order by idx to maintain the order from the form
        )
        
        issue_data["custom_users_assigned"] = user_assignments
        
        # Get tags for this issue
        tags = frappe.db.get_all(
            "Tag Link",
            filters={
                "document_type": "Issue",
                "document_name": issue_name
            },
            fields=["tag"],
            order_by="creation asc"
        )
        
        # Convert tags to a simple list of tag names
        issue_data["_user_tags"] = [tag.tag for tag in tags] if tags else []
        
        return issue_data
        
    except frappe.DoesNotExistError:
        # Issue was deleted, return None
        return None
        
    except Exception as e:
        frappe.log_error(f"Error in get_single_issue_with_assignments: {str(e)}")
        frappe.throw(_("Failed to fetch single issue: {0}").format(str(e)))


@frappe.whitelist()
def get_tag_colors():
    """
    Get all tag colors from Tag Categories
    Returns a mapping of tag names to their colors
    """
    try:
        # Check if Tag Category doctype exists
        if not frappe.db.exists("DocType", "Tag Category"):
            frappe.log_error("Tag Category doctype does not exist")
            return {}
        
        # Get all Tag Categories with their colors
        tag_categories = frappe.get_all(
            "Tag Category",
            fields=["tag_category_name", "category_color"],
            limit_page_length=0
        )
        
        tag_color_map = {}
        
        # For each category, get all tags that belong to it
        for category in tag_categories:
            if category.get("category_color"):
                try:
                    # Check if the custom_tag_category field exists on Tag doctype
                    if frappe.db.has_column("Tag", "custom_tag_category"):
                        # Get all tags in this category
                        tags_in_category = frappe.get_all(
                            "Tag",
                            fields=["name"],
                            filters={"custom_tag_category": category.tag_category_name},
                            limit_page_length=0
                        )
                        
                        # Map each tag to the category color
                        for tag in tags_in_category:
                            tag_color_map[tag.name] = category.category_color
                    
                    # Also map the category name itself as a tag (for direct matching)
                    tag_color_map[category.tag_category_name] = category.category_color
                    
                except Exception as inner_e:
                    frappe.log_error(f"Error processing category {category.tag_category_name}: {str(inner_e)}")
                    continue
        
        return tag_color_map
        
    except Exception as e:
        frappe.log_error(f"Error in get_tag_colors: {str(e)}")
        # Return empty dict instead of raising exception to prevent frontend errors
        return {}


@frappe.whitelist()
def issue_search(search_query="", limit=8):
    """
    Search issues for autocomplete suggestions
    Returns only essential fields: name, subject, status, raised_by, creation, description
    This function respects permissions by using frappe.get_list
    """
    try:
        # Convert string parameters
        limit = int(limit)
        
        # Return empty if query is too short
        if not search_query or len(search_query.strip()) < 2:
            return []
        
        search_query = search_query.strip()
        
        # Use frappe.get_list with or_filters to respect permissions
        or_filters = [
            ["name", "like", f"%{search_query}%"],
            ["subject", "like", f"%{search_query}%"],
            ["customer", "like", f"%{search_query}%"],
            ["raised_by", "like", f"%{search_query}%"]
        ]
        
        # Get issues using frappe.get_list to respect permissions
        issues = frappe.get_list(
            "Issue",
            fields=["name", "subject", "status", "raised_by", "creation", "description"],
            or_filters=or_filters,
            order_by="modified desc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        return issues
        
    except Exception as e:
        frappe.log_error(f"Error in issue_search: {str(e)}")
        frappe.throw(_("Failed to search issues: {0}").format(str(e)))


@frappe.whitelist()
def filter_issues_by_suggestion(suggestion_type, suggestion_value, limit_page_length=10, limit_start=0, order_by="creation desc"):
    """
    Filter issues based on selected suggestion from search
    This is called when user clicks on a search suggestion to filter the main table
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Build filters based on suggestion type and value
        filters = {}
        
        if suggestion_type == "name":
            filters["name"] = suggestion_value
        elif suggestion_type == "subject":
            filters["subject"] = ["like", f"%{suggestion_value}%"]
        elif suggestion_type == "customer":
            filters["customer"] = suggestion_value
        elif suggestion_type == "raised_by":
            filters["raised_by"] = suggestion_value
        elif suggestion_type == "status":
            filters["status"] = suggestion_value
        elif suggestion_type == "priority":
            filters["priority"] = suggestion_value
        elif suggestion_type == "issue_type":
            filters["issue_type"] = suggestion_value
        elif suggestion_type == "project":
            filters["project"] = suggestion_value
        else:
            # Default: search in multiple fields if type is not specified
            # Use frappe.get_list with or_filters to respect permissions
            or_filters = [
                ["name", "like", f"%{suggestion_value}%"],
                ["subject", "like", f"%{suggestion_value}%"],
                ["customer", "like", f"%{suggestion_value}%"],
                ["raised_by", "like", f"%{suggestion_value}%"]
            ]
            
            # Base fields to fetch from Issue doctype
            fields = [
                "name",
                "subject", 
                "status",
                "priority",
                "raised_by",
                "customer",
                "project",
                "issue_type",
                "creation",
                "modified",
                "owner",
                "description"
            ]
            
            # Get issues using frappe.get_list to respect permissions
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                or_filters=or_filters,
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
            
            # Add child table data and tags for each issue
            for issue in issues:
                # Get child table data for custom_users_assigned
                user_assignments = frappe.db.get_all(
                    "Team User Assignment",
                    filters={"parent": issue.name},
                    fields=["*"],
                    order_by="idx asc"
                )
                issue["custom_users_assigned"] = user_assignments
                
                # Get tags for this issue
                tags = frappe.db.get_all(
                    "Tag Link",
                    filters={
                        "document_type": "Issue",
                        "document_name": issue.name
                    },
                    fields=["tag"],
                    order_by="creation asc"
                )
                issue["_user_tags"] = [tag.tag for tag in tags] if tags else []
            
            return issues
        
        # For specific field filters, use the existing get_issues_with_assignments logic
        return get_issues_with_assignments(
            limit_page_length=limit_page_length,
            limit_start=limit_start,
            filters=filters,
            order_by=order_by
        )
        
    except Exception as e:
        frappe.log_error(f"Error in filter_issues_by_suggestion: {str(e)}")
        frappe.throw(_("Failed to filter issues by suggestion: {0}").format(str(e)))


@frappe.whitelist()
def get_issue_stats():
    """
    Get global issue statistics for the current user
    Returns stats that respect the same permission system as other functions
    """
    try:
        # Get all issues that the user can see (respects permissions)
        all_issues = frappe.get_list(
            "Issue",
            fields=[
                "name",
                "status",
                "raised_by",
                "custom_is_response_awaited",
                "custom_is_response_expected"
            ],
            limit_page_length=0,  # Get all records
            ignore_permissions=False
        )
        
        # Get current user
        current_user = frappe.session.user
        
        # Get current user's team(s) by checking their assignments across all issues
        user_teams = set()
        
        # Get all user assignments for issues the user can see
        if all_issues:
            issue_names = [issue.name for issue in all_issues]
            user_assignments = frappe.db.get_all(
                "Team User Assignment",
                filters={
                    "parent": ["in", issue_names],
                    "parenttype": "Issue",
                    "parentfield": "custom_users_assigned"
                },
                fields=["*"]  # Get all fields to debug what's available
            )
                        
            # Find current user's teams
            for assignment in user_assignments:
                # Handle different possible field names for user_assigned
                user_field = assignment.get('user_assigned') or assignment.get('user') or assignment.get('assigned_user')
                team_field = assignment.get('team')
                
                if user_field == current_user and team_field:
                    user_teams.add(team_field)
            
            # Create a mapping of issue to its assignments for efficient lookup
            issue_assignments = {}
            for assignment in user_assignments:
                if assignment.parent not in issue_assignments:
                    issue_assignments[assignment.parent] = []
                issue_assignments[assignment.parent].append(assignment)
        else:
            issue_assignments = {}
        
        # Calculate statistics
        stats = {
            "team_tickets": len(all_issues),
            "open_tickets": 0,
            "assigned_to_me": 0,
            "actionable_tickets": 0,
            "response_tickets": 0
        }
        
        for issue in all_issues:
            issue_name = issue.name
            issue_status = issue.status
            
            # Get assignments for this issue
            assignments = issue_assignments.get(issue_name, [])
            
            # Check if assigned to current user
            is_assigned_to_me = any(
                (assignment.get('user_assigned') or assignment.get('user') or assignment.get('assigned_user')) == current_user 
                for assignment in assignments
            )
            
            if is_assigned_to_me:
                stats["assigned_to_me"] += 1
            
            # Open tickets: no one from current user's team is assigned (regardless of status)
            has_team_assignment = any(
                assignment.team in user_teams 
                for assignment in assignments 
                if assignment.team
            )
            if not has_team_assignment:
                stats["open_tickets"] += 1
            
            # Actionable tickets: Customer awaits reply (custom_is_response_expected = 1)
            if issue.custom_is_response_expected:
                stats["actionable_tickets"] += 1
            
            # Response tickets: Awaiting customer response (custom_is_response_awaited = 1)
            if issue.custom_is_response_awaited:
                stats["response_tickets"] += 1
        
        return stats
        
    except Exception as e:
        frappe.log_error(f"Error in get_issue_stats: {str(e)}")
        frappe.throw(_("Failed to get issue statistics: {0}").format(str(e)))


@frappe.whitelist()
def get_issues_by_stat_filter(stat_type, limit_page_length=10, limit_start=0, order_by="creation desc"):
    """
    Get issues filtered by stat type (team_tickets, open_tickets, assigned_to_me, etc.)
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Get current user
        current_user = frappe.session.user
        
        # Base fields to fetch from Issue doctype
        fields = [
            "name",
            "subject", 
            "status",
            "priority",
            "raised_by",
            "customer",
            "project",
            "issue_type",
            "creation",
            "modified",
            "owner",
            "description"
        ]
        
        # Build filters based on stat type
        if stat_type == "team_tickets":
            # All issues user can see (no additional filtering)
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
        
        elif stat_type == "assigned_to_me":
            # Get all issues first, then filter by assignment
            all_issues = frappe.get_list(
                "Issue",
                fields=fields + ["name"],
                limit_page_length=0,  # Get all to filter
                ignore_permissions=False
            )
            
            # Get user assignments for all issues
            if all_issues:
                issue_names = [issue.name for issue in all_issues]
                user_assignments = frappe.db.get_all(
                    "Team User Assignment",
                    filters={
                        "parent": ["in", issue_names],
                        "parenttype": "Issue",
                        "parentfield": "custom_users_assigned",
                        "user_assigned": current_user
                    },
                    fields=["parent"]
                )
                
                assigned_issue_names = [assignment.parent for assignment in user_assignments]
                
                # Filter issues to only those assigned to current user
                filtered_issues = [issue for issue in all_issues if issue.name in assigned_issue_names]
                
                # Apply pagination to filtered results
                start_idx = limit_start
                end_idx = limit_start + limit_page_length
                issues = filtered_issues[start_idx:end_idx]
            else:
                issues = []
        
        elif stat_type == "open_tickets":
            # Get all issues first, then filter by team assignment logic
            all_issues = frappe.get_list(
                "Issue",
                fields=fields + ["name"],
                limit_page_length=0,  # Get all to filter
                ignore_permissions=False
            )
            
            if all_issues:
                issue_names = [issue.name for issue in all_issues]
                
                # Get current user's teams
                user_assignments = frappe.db.get_all(
                    "Team User Assignment",
                    filters={
                        "parent": ["in", issue_names],
                        "parenttype": "Issue",
                        "parentfield": "custom_users_assigned"
                    },
                    fields=["*"]
                )
                
                user_teams = set()
                for assignment in user_assignments:
                    if assignment.user_assigned == current_user and assignment.team:
                        user_teams.add(assignment.team)
                
                # Create mapping of issues to their team assignments
                issue_team_assignments = {}
                for assignment in user_assignments:
                    if assignment.parent not in issue_team_assignments:
                        issue_team_assignments[assignment.parent] = []
                    if assignment.team:
                        issue_team_assignments[assignment.parent].append(assignment.team)
                
                # Filter for open tickets (no team member assigned)
                open_issues = []
                for issue in all_issues:
                    assigned_teams = issue_team_assignments.get(issue.name, [])
                    has_team_assignment = any(team in user_teams for team in assigned_teams)
                    if not has_team_assignment:
                        open_issues.append(issue)
                
                # Apply pagination to filtered results
                start_idx = limit_start
                end_idx = limit_start + limit_page_length
                issues = open_issues[start_idx:end_idx]
            else:
                issues = []
        
        elif stat_type == "actionable_tickets":
            # Issues where customer awaits reply (custom_is_response_expected = 1)
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters={"custom_is_response_expected": 1},
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
        
        elif stat_type == "response_tickets":
            # Issues awaiting customer response (custom_is_response_awaited = 1)
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters={"custom_is_response_awaited": 1},
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
        
        else:
            # Default to all issues
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                order_by=order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
        
        # Add child table data and tags for each issue
        for issue in issues:
            # Get child table data for custom_users_assigned
            user_assignments = frappe.db.get_all(
                "Team User Assignment",
                filters={"parent": issue.name},
                fields=["*"],
                order_by="idx asc"
            )
            issue["custom_users_assigned"] = user_assignments
            
            # Get tags for this issue
            tags = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "document_name": issue.name
                },
                fields=["tag"],
                order_by="creation asc"
            )
            issue["_user_tags"] = [tag.tag for tag in tags] if tags else []
        
        return issues
        
    except Exception as e:
        frappe.log_error(f"Error in get_issues_by_stat_filter: {str(e)}")
        frappe.throw(_("Failed to filter issues by stat: {0}").format(str(e)))


@frappe.whitelist()
def get_stat_filter_count(stat_type):
    """
    Get count of issues for a specific stat filter type
    """
    try:
        # Get current user
        current_user = frappe.session.user
        
        if stat_type == "team_tickets":
            # All issues user can see
            all_issues = frappe.get_list(
                "Issue",
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
            return len(all_issues)
        
        elif stat_type == "assigned_to_me":
            # Get all issues first, then filter by assignment
            all_issues = frappe.get_list(
                "Issue",
                fields=["name"],
                limit_page_length=0,
                ignore_permissions=False
            )
            
            if all_issues:
                issue_names = [issue.name for issue in all_issues]
                user_assignments = frappe.db.get_all(
                    "Team User Assignment",
                    filters={
                        "parent": ["in", issue_names],
                        "parenttype": "Issue",
                        "parentfield": "custom_users_assigned",
                        "user_assigned": current_user
                    },
                    fields=["parent"]
                )
                return len(user_assignments)
            return 0
        
        elif stat_type == "open_tickets":
            # Use the same logic as in get_issue_stats
            all_issues = frappe.get_list(
                "Issue",
                fields=["name"],
                limit_page_length=0,
                ignore_permissions=False
            )
            
            if all_issues:
                issue_names = [issue.name for issue in all_issues]
                user_assignments = frappe.db.get_all(
                    "Team User Assignment",
                    filters={
                        "parent": ["in", issue_names],
                        "parenttype": "Issue",
                        "parentfield": "custom_users_assigned"
                    },
                    fields=["*"]
                )
                
                user_teams = set()
                for assignment in user_assignments:
                    if assignment.user_assigned == current_user and assignment.team:
                        user_teams.add(assignment.team)
                
                issue_team_assignments = {}
                for assignment in user_assignments:
                    if assignment.parent not in issue_team_assignments:
                        issue_team_assignments[assignment.parent] = []
                    if assignment.team:
                        issue_team_assignments[assignment.parent].append(assignment.team)
                
                open_count = 0
                for issue in all_issues:
                    assigned_teams = issue_team_assignments.get(issue.name, [])
                    has_team_assignment = any(team in user_teams for team in assigned_teams)
                    if not has_team_assignment:
                        open_count += 1
                
                return open_count
            return 0
        
        elif stat_type == "actionable_tickets":
            result = frappe.get_list(
                "Issue",
                filters={"custom_is_response_expected": 1},
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
            return len(result)
        
        elif stat_type == "response_tickets":
            result = frappe.get_list(
                "Issue",
                filters={"custom_is_response_awaited": 1},
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
            return len(result)
        
        else:
            # Default to all issues
            all_issues = frappe.get_list(
                "Issue",
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
            return len(all_issues)
        
    except Exception as e:
        frappe.log_error(f"Error in get_stat_filter_count: {str(e)}")
        frappe.throw(_("Failed to get stat filter count: {0}").format(str(e)))


@frappe.whitelist()
def get_filtered_issues_count(suggestion_type, suggestion_value):
    """
    Get count of filtered issues for pagination
    This function respects the same permission system as other functions
    """
    try:
        # Build filters based on suggestion type and value
        if suggestion_type == "name":
            filters = {"name": suggestion_value}
        elif suggestion_type == "subject":
            filters = {"subject": ["like", f"%{suggestion_value}%"]}
        elif suggestion_type == "customer":
            filters = {"customer": suggestion_value}
        elif suggestion_type == "raised_by":
            filters = {"raised_by": suggestion_value}
        elif suggestion_type == "status":
            filters = {"status": suggestion_value}
        elif suggestion_type == "priority":
            filters = {"priority": suggestion_value}
        elif suggestion_type == "issue_type":
            filters = {"issue_type": suggestion_value}
        elif suggestion_type == "project":
            filters = {"project": suggestion_value}
        else:
            # Default: count with complex OR conditions using frappe.get_list to respect permissions
            # Build a complex filter for multiple field search
            or_filters = [
                ["name", "like", f"%{suggestion_value}%"],
                ["subject", "like", f"%{suggestion_value}%"],
                ["customer", "like", f"%{suggestion_value}%"],
                ["raised_by", "like", f"%{suggestion_value}%"]
            ]
            
            result = frappe.get_list(
                "Issue",
                or_filters=or_filters,
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
            
            return len(result)
        
        # For specific field filters, use frappe.get_list to respect permissions
        result = frappe.get_list(
            "Issue",
            filters=filters,
            limit_page_length=0,
            as_list=True,
            ignore_permissions=False
        )
        
        return len(result)
        
    except Exception as e:
        frappe.log_error(f"Error in get_filtered_issues_count: {str(e)}")
        frappe.throw(_("Failed to get filtered issues count: {0}").format(str(e)))