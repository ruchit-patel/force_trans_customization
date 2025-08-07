import frappe
from frappe import _
from datetime import datetime
import json


def process_filter_list(filters):
    """
    Process the new filter list structure from frontend
    Converts filter objects to frappe.get_list compatible format
    """
    processed_filters = {}
    or_filters = []
    
    if not filters or not isinstance(filters, list):
        return processed_filters, or_filters
    
    for filter_obj in filters:
        if not isinstance(filter_obj, dict):
            continue
            
        field = filter_obj.get('field')
        operator = filter_obj.get('operator')
        value = filter_obj.get('value')
        
        if not field or not operator or value is None or value == '':
            continue
            
        # Convert string values to appropriate types
        processed_value = convert_filter_value(field, value, operator)
        
        # Handle different operators
        if operator == 'equals':
            processed_filters[field] = processed_value
        elif operator == 'not_equals':
            processed_filters[field] = ['!=', processed_value]
        elif operator == 'like' or operator == 'contains':
            if field == 'subject':
                # Special handling for subject - search in both subject and description
                or_filters.extend([
                    ['subject', 'like', f'%{processed_value}%'],
                    ['description', 'like', f'%{processed_value}%']
                ])
            else:
                processed_filters[field] = ['like', f'%{processed_value}%']
        elif operator == 'starts_with':
            processed_filters[field] = ['like', f'{processed_value}%']
        elif operator == 'ends_with':
            processed_filters[field] = ['like', f'%{processed_value}']
        elif operator == 'greater_than':
            processed_filters[field] = ['>', processed_value]
        elif operator == 'less_than':
            processed_filters[field] = ['<', processed_value]
        elif operator == 'greater_than_equal':
            processed_filters[field] = ['>=', processed_value]
        elif operator == 'less_than_equal':
            processed_filters[field] = ['<=', processed_value]
        elif operator == 'in':
            # Handle comma-separated values or arrays
            if isinstance(processed_value, str):
                values = [v.strip() for v in processed_value.split(',') if v.strip()]
            else:
                values = processed_value if isinstance(processed_value, list) else [processed_value]
            if values:
                processed_filters[field] = ['in', values]
        elif operator == 'not_in':
            if isinstance(processed_value, str):
                values = [v.strip() for v in processed_value.split(',') if v.strip()]
            else:
                values = processed_value if isinstance(processed_value, list) else [processed_value]
            if values:
                processed_filters[field] = ['not in', values]
        elif operator == 'between':
            # Handle date/datetime ranges - value should be "start,end"
            if isinstance(processed_value, str) and ',' in processed_value:
                parts = [p.strip() for p in processed_value.split(',')]
                if len(parts) == 2:
                    processed_filters[field] = ['between', parts]
        elif operator == 'has' or operator == 'has_any':
            # For tags - search in _user_tags using custom logic
            # This will be handled separately in tag filtering
            if field == '_user_tags':
                # We'll handle this in a special way since tags are in a separate table
                continue
        else:
            # Default to equals
            processed_filters[field] = processed_value
    
    return processed_filters, or_filters


def convert_filter_value(field, value, operator):
    """
    Convert filter values to appropriate types based on field type
    """
    # Field type mapping
    field_types = {
        'creation': 'datetime',
        'modified': 'datetime',
        'priority': 'select',
        'status': 'select',
        'issue_type': 'select',
        'subject': 'text',
        'description': 'text',
        'raised_by': 'email',
        'customer': 'link',
        'project': 'link',
        'owner': 'link',
        '_user_tags': 'tags'
    }
    
    field_type = field_types.get(field, 'text')
    
    # Convert based on field type
    if field_type in ['datetime', 'date']:
        # Handle datetime conversion
        if isinstance(value, str) and value:
            try:
                # Try parsing different datetime formats
                if 'T' in value:  # ISO format
                    return value
                elif '-' in value and ' ' in value:  # YYYY-MM-DD HH:MM:SS
                    return value
                elif '-' in value:  # YYYY-MM-DD
                    return value
                else:
                    return value
            except:
                return value
    
    return value


def get_tag_filters(filters):
    """
    Extract tag-related filters from the filter list
    """
    tag_filters = []
    if not filters or not isinstance(filters, list):
        return tag_filters
    
    for filter_obj in filters:
        if isinstance(filter_obj, dict) and filter_obj.get('field') == '_user_tags':
            tag_filters.append(filter_obj)
    
    return tag_filters


def get_issues_by_tag_filters(tag_filters):
    """
    Get issue names that match tag filters
    Returns None if no tag filters, empty list if no matches, list of names if matches found
    """
    if not tag_filters:
        return None
    
    issue_names_sets = []
    
    for tag_filter in tag_filters:
        operator = tag_filter.get('operator')
        value = tag_filter.get('value')
        
        if not value:
            continue
        
        # Parse tags from value
        if isinstance(value, str):
            tags = [t.strip() for t in value.split(',') if t.strip()]
        else:
            tags = [value] if not isinstance(value, list) else value
        
        if not tags:
            continue
        
        issue_names = set()
        
        if operator == 'has' or operator == 'has_any':
            # Issues that have ANY of the specified tags
            tag_links = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "tag": ["in", tags]
                },
                fields=["document_name"]
            )
            issue_names.update([link.document_name for link in tag_links])
        
        elif operator == 'has_all':
            # Issues that have ALL of the specified tags
            if len(tags) == 1:
                # Single tag case
                tag_links = frappe.db.get_all(
                    "Tag Link",
                    filters={
                        "document_type": "Issue",
                        "tag": tags[0]
                    },
                    fields=["document_name"]
                )
                issue_names.update([link.document_name for link in tag_links])
            else:
                # Multiple tags - need all
                potential_issues = frappe.db.get_all(
                    "Tag Link",
                    filters={
                        "document_type": "Issue",
                        "tag": ["in", tags]
                    },
                    fields=["document_name", "tag"]
                )
                
                # Group by issue name
                issue_tag_counts = {}
                for link in potential_issues:
                    if link.document_name not in issue_tag_counts:
                        issue_tag_counts[link.document_name] = set()
                    issue_tag_counts[link.document_name].add(link.tag)
                
                # Find issues that have all required tags
                required_tags_set = set(tags)
                for issue_name, issue_tags in issue_tag_counts.items():
                    if required_tags_set.issubset(issue_tags):
                        issue_names.add(issue_name)
        
        elif operator == 'not_has':
            # Issues that do NOT have any of the specified tags
            all_issues = frappe.db.get_all(
                "Issue",
                fields=["name"]
            )
            
            issues_with_tags = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "tag": ["in", tags]
                },
                fields=["document_name"]
            )
            
            issues_with_tags_set = {link.document_name for link in issues_with_tags}
            issue_names.update([
                issue.name for issue in all_issues 
                if issue.name not in issues_with_tags_set
            ])
        
        if issue_names:
            issue_names_sets.append(issue_names)
    
    # Intersect all sets (AND operation between different tag filters)
    if not issue_names_sets:
        return None
    
    result = issue_names_sets[0]
    for issue_set in issue_names_sets[1:]:
        result = result.intersection(issue_set)
    
    return list(result)


@frappe.whitelist()
def get_issues_with_assignments(limit_page_length=10, limit_start=0, filters=None, order_by="creation desc"):
    """
    Get issues list with custom_users_assigned child table data
    Enhanced to handle complex filter objects from frontend
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Handle filters
        if filters is None:
            filters = []
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
        
        # Process new filter structure from frontend
        processed_filters, or_filters = process_filter_list(filters)
        
        # Handle tag filters separately (since tags are in Tag Link table)
        tag_filters = get_tag_filters(filters)
        issue_names_from_tags = None
        
        if tag_filters:
            issue_names_from_tags = get_issues_by_tag_filters(tag_filters)
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    # No issues match tag filters
                    return []
                else:
                    # Add name filter to restrict to issues matching tags
                    processed_filters['name'] = ['in', issue_names_from_tags]
        
        # Get issues using frappe.get_list with enhanced filter handling
        if or_filters:
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
    Enhanced to handle complex filter objects from frontend
    """
    try:
        # Handle filters
        if filters is None:
            filters = []
        elif isinstance(filters, str):
            filters = json.loads(filters)
        
        # Process new filter structure from frontend
        processed_filters, or_filters = process_filter_list(filters)
        
        # Handle tag filters separately
        tag_filters = get_tag_filters(filters)
        issue_names_from_tags = None
        
        if tag_filters:
            issue_names_from_tags = get_issues_by_tag_filters(tag_filters)
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    # No issues match tag filters
                    return 0
                else:
                    # Add name filter to restrict to issues matching tags
                    processed_filters['name'] = ['in', issue_names_from_tags]
        
        # Use frappe.get_list to get count while respecting permissions
        if or_filters:
            result = frappe.get_list(
                "Issue",
                filters=processed_filters,
                or_filters=or_filters,
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
            )
        else:
            result = frappe.get_list(
                "Issue",
                filters=processed_filters,
                limit_page_length=0,
                as_list=True,
                ignore_permissions=False
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
def get_issues_by_stat_filter(stat_type, limit_page_length=10, limit_start=0, order_by="creation desc", filters=None):
    """
    Get issues filtered by stat type (team_tickets, open_tickets, assigned_to_me, etc.)
    Enhanced to accept additional filters from the frontend
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Handle additional filters from frontend
        if filters is None:
            filters = []
        elif isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except:
                filters = []
        
        # Process additional filters
        additional_filters, additional_or_filters = process_filter_list(filters)
        
        # Handle tag filters from additional filters
        tag_filters = get_tag_filters(filters)
        issue_names_from_tags = None
        
        if tag_filters:
            issue_names_from_tags = get_issues_by_tag_filters(tag_filters)
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return []  # No issues match tag filters
        
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
            # All issues user can see with additional filters
            combined_filters = additional_filters.copy()
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return []  # No issues match tag filters
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
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
            combined_filters = additional_filters.copy()
            combined_filters["custom_is_response_expected"] = 1
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return []
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    order_by=order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
        
        elif stat_type == "response_tickets":
            # Issues awaiting customer response (custom_is_response_awaited = 1)
            combined_filters = additional_filters.copy()
            combined_filters["custom_is_response_awaited"] = 1
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return []
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
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
def get_stat_filter_count(stat_type, filters=None):
    """
    Get count of issues for a specific stat filter type
    Enhanced to accept additional filters from the frontend
    """
    try:
        # Handle additional filters from frontend
        if filters is None:
            filters = []
        elif isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except:
                filters = []
        
        # Process additional filters
        additional_filters, additional_or_filters = process_filter_list(filters)
        
        # Handle tag filters from additional filters
        tag_filters = get_tag_filters(filters)
        issue_names_from_tags = None
        
        if tag_filters:
            issue_names_from_tags = get_issues_by_tag_filters(tag_filters)
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return 0  # No issues match tag filters
        
        # Get current user
        current_user = frappe.session.user
        
        if stat_type == "team_tickets":
            # All issues user can see with additional filters
            combined_filters = additional_filters.copy()
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return 0  # No issues match tag filters
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                all_issues = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    limit_page_length=0,
                    as_list=True,
                    ignore_permissions=False
                )
            else:
                all_issues = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
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
            # Issues where customer awaits reply with additional filters
            combined_filters = additional_filters.copy()
            combined_filters["custom_is_response_expected"] = 1
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return 0
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                result = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    limit_page_length=0,
                    as_list=True,
                    ignore_permissions=False
                )
            else:
                result = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
                    limit_page_length=0,
                    as_list=True,
                    ignore_permissions=False
                )
            return len(result)
        
        elif stat_type == "response_tickets":
            # Issues awaiting customer response with additional filters
            combined_filters = additional_filters.copy()
            combined_filters["custom_is_response_awaited"] = 1
            
            # Apply tag filtering if needed
            if issue_names_from_tags is not None:
                if len(issue_names_from_tags) == 0:
                    return 0
                combined_filters['name'] = ['in', issue_names_from_tags]
            
            if additional_or_filters:
                result = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    limit_page_length=0,
                    as_list=True,
                    ignore_permissions=False
                )
            else:
                result = frappe.get_list(
                    "Issue",
                    filters=combined_filters,
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


@frappe.whitelist()
def search_users(search_query="", limit=10, doctype_filter="User"):
    """
    Search users for autocomplete in filters
    Support searching in User doctype with different filter criteria
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            return []
        
        search_query = search_query.strip()
        
        # Base fields to return
        fields = ["name", "full_name", "email", "enabled"]
        
        # Build filters based on doctype_filter
        filters = {"enabled": 1}  # Only enabled users
        
        if doctype_filter == "User":
            # Search in all users
            or_filters = [
                ["name", "like", f"%{search_query}%"],
                ["full_name", "like", f"%{search_query}%"],
                ["email", "like", f"%{search_query}%"]
            ]
        else:
            # Default to User doctype
            or_filters = [
                ["name", "like", f"%{search_query}%"],
                ["full_name", "like", f"%{search_query}%"],
                ["email", "like", f"%{search_query}%"]
            ]
        
        # Get users using frappe.get_list to respect permissions
        users = frappe.get_list(
            "User",
            fields=fields,
            filters=filters,
            or_filters=or_filters,
            order_by="full_name asc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        # Format results for frontend
        results = []
        for user in users:
            display_name = user.full_name or user.name
            if user.email and user.email != user.name:
                display_name += f" ({user.email})"
            
            results.append({
                "value": user.name,
                "label": display_name,
                "subtitle": user.email or user.name,
                "type": "user"
            })
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in search_users: {str(e)}")
        frappe.throw(_("Failed to search users: {0}").format(str(e)))


@frappe.whitelist()
def search_customers(search_query="", limit=10):
    """
    Search customers for autocomplete in filters
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            return []
        
        search_query = search_query.strip()
        
        # Get customers using frappe.get_list to respect permissions
        or_filters = [
            ["name", "like", f"%{search_query}%"],
            ["customer_name", "like", f"%{search_query}%"]
        ]
        
        customers = frappe.get_list(
            "Customer",
            fields=["name", "customer_name", "customer_group", "territory"],
            or_filters=or_filters,
            order_by="customer_name asc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        # Format results for frontend
        results = []
        for customer in customers:
            display_name = customer.customer_name or customer.name
            subtitle = f"{customer.customer_group or ''} • {customer.territory or ''}".strip(" •")
            
            results.append({
                "value": customer.name,
                "label": display_name,
                "subtitle": subtitle if subtitle else customer.name,
                "type": "customer"
            })
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in search_customers: {str(e)}")
        frappe.throw(_("Failed to search customers: {0}").format(str(e)))


@frappe.whitelist()
def search_tags(search_query="", limit=15):
    """
    Search tags for autocomplete in filters
    Returns both existing tags from Tag doctype and tags currently used in issues
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            # If no search query, return most frequently used tags in issues
            tag_links = frappe.db.get_all(
                "Tag Link",
                filters={"document_type": "Issue"},
                fields=["tag", "count(name) as usage_count"],
                group_by="tag",
                order_by="usage_count desc",
                limit=limit
            )
            
            results = []
            for tag_link in tag_links:
                # Get tag color if available
                try:
                    tag_doc = frappe.get_doc("Tag", tag_link.tag)
                    tag_color = getattr(tag_doc, 'tag_color', None) or '#gray'
                except:
                    tag_color = '#gray'
                
                results.append({
                    "value": tag_link.tag,
                    "label": tag_link.tag,
                    "subtitle": f"Used in {tag_link.usage_count} issue(s)",
                    "type": "tag",
                    "color": tag_color
                })
            
            return results
        
        search_query = search_query.strip()
        
        # Search in existing tags first
        tag_results = []
        try:
            tags = frappe.get_list(
                "Tag",
                fields=["name", "tag_color"],
                filters=[["name", "like", f"%{search_query}%"]],
                order_by="name asc",
                limit_page_length=limit,
                ignore_permissions=False
            )
            
            for tag in tags:
                # Check if this tag is used in issues
                usage_count = frappe.db.count(
                    "Tag Link",
                    filters={"document_type": "Issue", "tag": tag.name}
                )
                
                tag_results.append({
                    "value": tag.name,
                    "label": tag.name,
                    "subtitle": f"Used in {usage_count} issue(s)" if usage_count > 0 else "Available tag",
                    "type": "tag",
                    "color": tag.tag_color or '#gray'
                })
        except:
            # If Tag doctype doesn't exist or has issues, continue with tag links search
            pass
        
        # Also search in tag links for tags actually used in issues
        if len(tag_results) < limit:
            remaining_limit = limit - len(tag_results)
            existing_tag_names = [tag["value"] for tag in tag_results]
            
            tag_links = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "tag": ["like", f"%{search_query}%"]
                },
                fields=["tag", "count(name) as usage_count"],
                group_by="tag",
                order_by="usage_count desc",
                limit=remaining_limit * 2  # Get extra in case of duplicates
            )
            
            for tag_link in tag_links:
                if tag_link.tag not in existing_tag_names and len(tag_results) < limit:
                    # Try to get tag color
                    try:
                        tag_doc = frappe.get_doc("Tag", tag_link.tag)
                        tag_color = getattr(tag_doc, 'tag_color', None) or '#gray'
                    except:
                        tag_color = '#gray'
                    
                    tag_results.append({
                        "value": tag_link.tag,
                        "label": tag_link.tag,
                        "subtitle": f"Used in {tag_link.usage_count} issue(s)",
                        "type": "tag",
                        "color": tag_color
                    })
        
        return tag_results[:limit]
        
    except Exception as e:
        frappe.log_error(f"Error in search_tags: {str(e)}")
        frappe.throw(_("Failed to search tags: {0}").format(str(e)))