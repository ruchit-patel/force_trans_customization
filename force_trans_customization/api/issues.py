import frappe
from frappe import _
from datetime import datetime
import json


def process_order_by(order_by_param):
    """
    Process order_by parameter to support multiple column sorting
    Input can be:
    - String: "creation desc" or "creation,modified desc" 
    - List: [{"field": "creation", "direction": "desc"}, {"field": "modified", "direction": "asc"}]
    - Dict: {"field": "creation", "direction": "desc"}
    
    Returns: Frappe-compatible order_by string
    """
    if not order_by_param:
        return "creation desc"
    
    # If it's already a simple string, return as-is
    if isinstance(order_by_param, str):
        return order_by_param
    
    # If it's a list of sort objects
    if isinstance(order_by_param, list):
        order_parts = []
        for sort_obj in order_by_param:
            if isinstance(sort_obj, dict):
                field = sort_obj.get('field', 'creation')
                direction = sort_obj.get('direction', 'desc').lower()
                if direction not in ['asc', 'desc']:
                    direction = 'desc'
                order_parts.append(f"{field} {direction}")
            elif isinstance(sort_obj, str):
                order_parts.append(sort_obj)
        return ", ".join(order_parts) if order_parts else "creation desc"
    
    # If it's a single sort object
    if isinstance(order_by_param, dict):
        field = order_by_param.get('field', 'creation')
        direction = order_by_param.get('direction', 'desc').lower()
        if direction not in ['asc', 'desc']:
            direction = 'desc'
        return f"{field} {direction}"
    
    return "creation desc"


def get_valid_sort_fields():
    """
    Get list of valid sortable fields for Issue doctype
    """
    return [
        'name', 'subject', 'status', 'priority', 'raised_by', 
        'customer', 'project', 'issue_type', 'creation', 'modified', 
        'owner', 'first_responded_on', 'resolution_time'
    ]


def validate_and_clean_order_by(order_by_str):
    """
    Validate and clean the order_by string to prevent SQL injection
    and ensure only valid fields are used
    """
    if not order_by_str or not isinstance(order_by_str, str):
        return "creation desc"
    
    valid_fields = get_valid_sort_fields()
    valid_directions = ['asc', 'desc']
    
    # Split by comma for multiple sorts
    parts = [part.strip() for part in order_by_str.split(',')]
    cleaned_parts = []
    
    for part in parts:
        # Split field and direction
        tokens = part.strip().split()
        if len(tokens) >= 2:
            field = tokens[0].strip()
            direction = tokens[1].strip().lower()
        elif len(tokens) == 1:
            field = tokens[0].strip()
            direction = 'desc'  # Default direction
        else:
            continue  # Skip invalid parts
        
        # Validate field and direction
        if field in valid_fields and direction in valid_directions:
            cleaned_parts.append(f"{field} {direction}")
    
    return ", ".join(cleaned_parts) if cleaned_parts else "creation desc"


def process_filter_list(filters):
    """
    Process the new filter list structure from frontend
    Converts filter objects to frappe.get_list compatible format
    """
    processed_filters = {}
    or_filters = []
    
    if not filters or not isinstance(filters, list):
        return processed_filters, or_filters
    
    
    for i, filter_obj in enumerate(filters):
        if not isinstance(filter_obj, dict):
            continue
            
        field = filter_obj.get('field')
        operator = filter_obj.get('operator')
        value = filter_obj.get('value')
        if not field or not operator or value is None or value == '':
            continue
            
        # Convert string values to appropriate types
        processed_value = convert_filter_value(field, value, operator)
        
        print(f" operator : {operator} --- processed_value : {processed_value} ")
        # Handle different operators
        if operator == 'equals' or operator == 'is':
            # Special handling for child table fields - skip custom_users_assigned only
            if field == 'custom_users_assigned':
                # Child table fields will be handled separately in get_child_table_filters
                continue
            # Special handling for date fields - convert to between operator for exact date match
            elif field in ['creation', 'modified'] and isinstance(processed_value, str) and len(processed_value) == 10:
                # For date equals, convert to between start and end of day
                start_datetime = f"{processed_value} 00:00:00"
                end_datetime = f"{processed_value} 23:59:59"
                processed_filters[field] = ['between', [start_datetime, end_datetime]]
            else:
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
            # Special handling for child table fields - skip custom_users_assigned only  
            if field == 'custom_users_assigned':
                # Child table fields will be handled separately in get_child_table_filters
                continue
            # Handle comma-separated values or arrays
            if isinstance(processed_value, str):
                values = [v.strip() for v in processed_value.split(',') if v.strip()]
            else:
                values = processed_value if isinstance(processed_value, list) else [processed_value]
            if values:
                processed_filters[field] = ['in', values]
        elif operator == 'not_in':
            # Special handling for child table fields - skip custom_users_assigned only
            if field == 'custom_users_assigned':
                # Child table fields will be handled separately in get_child_table_filters  
                continue
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
        elif operator == 'has' or operator == 'has_all' or operator == 'not_has':
            # For tags - search in _user_tags using custom logic
            # This will be handled separately in tag filtering
            if field == '_user_tags':
                # We'll handle this in a special way since tags are in a separate table
                continue
        else:
            # Default to equals
            processed_filters[field] = processed_value
    
    return processed_filters, or_filters


def get_latest_communications(issue_names):
    """
    Get the latest email communication for each issue
    Returns dict with issue_name as key and communication data as value
    """
    if not issue_names:
        return {}
    
    try:
        # Get the latest communication for each issue in a single query
        communications = frappe.db.sql("""
            SELECT 
                reference_name,
                subject,
                content,
                sent_or_received,
                creation,
                sender,
                recipients,
                _seen 
            FROM `tabCommunication`
            WHERE 
                reference_doctype = 'Issue'
                AND reference_name IN %s
                AND communication_type = 'Communication'
                AND content IS NOT NULL
                AND content != ''
            ORDER BY reference_name, creation DESC
        """, [issue_names], as_dict=True)
        
        # Group by issue and get the latest communication for each
        latest_communications = {}
        unread_count = 0
        import json
        for comm in communications:
            issue_name = comm.reference_name
            if issue_name not in latest_communications:
                # This is the latest communication for this issue (due to ORDER BY creation DESC)
                if comm._seen:
                    try:
                        seen_list = json.loads(comm._seen) if isinstance(comm._seen, str) else comm._seen
                    except Exception:
                        seen_list = []

                is_readed = frappe.session.user in seen_list
                if not is_readed:
                        unread_count += 1

                latest_communications[issue_name] = {
                    'subject': comm.subject,
                    'content': comm.content[:500] if comm.content else '',  # Limit content length
                    'sent_or_received': comm.sent_or_received,
                    'creation': comm.creation,
                    'sender': comm.sender,
                    'recipients': comm.recipients,
                    'seen': frappe.session.user in seen_list
                }
        return latest_communications,unread_count
        
    except Exception as e:
        frappe.log_error(f"Error fetching communications: {str(e)}")
        return {}


def convert_filter_value(field, value, operator):
    """
    Convert filter values to appropriate types based on field type
    """
    # Field type mapping
    field_types = {
        'creation': 'date',
        'modified': 'date',
        'status': 'select',
        'subject': 'text',
        'description': 'text',
        'raised_by': 'email',
        'customer': 'link',
        'contact': 'link',
        'lead': 'link',
        'custom_assigned_csm_team': 'link',
        'custom_users_assigned': 'link',
        '_user_tags': 'tags'
    }
    
    field_type = field_types.get(field, 'text')
    
    # Convert based on field type
    if field_type == 'date':
        # Handle date conversion - convert date to proper format for frappe filtering
        if isinstance(value, str) and value:
            try:
                # Input format: YYYY-MM-DD (from date input)
                if '-' in value and len(value) == 10:  # YYYY-MM-DD format
                    if operator in ['greater_than', 'greater_than_equal', '>', '>=']:
                        # For "after" dates, add time 00:00:00 to include the whole day
                        return f"{value} 00:00:00"
                    elif operator in ['less_than', 'less_than_equal', '<', '<=']:
                        # For "before" dates, add time 23:59:59 to include the whole day
                        return f"{value} 23:59:59"
                    elif operator == 'equals':
                        # For exact date match, we need to use between operator
                        return value
                    else:
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


def get_child_table_filters(filters):
    """
    Extract child table filters from the filter list (custom_users_assigned only)
    """
    child_filters = []
    if not filters or not isinstance(filters, list):
        return child_filters
    
    for filter_obj in filters:
        if isinstance(filter_obj, dict) and filter_obj.get('field') == 'custom_users_assigned':
            child_filters.append(filter_obj)
    
    return child_filters


def get_issues_by_child_table_filters(child_filters):
    """
    Get issue names that match child table filters
    Returns None if no child filters, empty list if no matches, list of names if matches found
    """
    if not child_filters:
        return None
    
    
    issue_names_sets = []
    
    for i, child_filter in enumerate(child_filters):
        field = child_filter.get('field')
        operator = child_filter.get('operator')
        value = child_filter.get('value')
        
        if not value:
            continue
        
        # Parse values from value
        if isinstance(value, str):
            values = [v.strip() for v in value.split(',') if v.strip()]
        else:
            values = [value] if not isinstance(value, list) else value
        
        
        if not values:
            continue
        
        issue_names = set()
        
        # Determine the child table name based on field
        if field == 'custom_users_assigned':
            child_table = "Team User Assignment"
            child_field = "user_assigned"
        else:
            continue

        
        # Check if table exists
        if not frappe.db.table_exists(child_table):
            continue
        
        if operator == 'in':
            if len(values) == 1:
                # Single value case - find issues that have this specific user assigned
                child_links = frappe.db.get_all(
                    child_table,
                    filters={
                        "parenttype": "Issue",
                        "parentfield": field,
                        child_field: values[0]
                    },
                    fields=["parent"]
                )
                issue_names.update([link.parent for link in child_links])
            else:
                # Multiple values - different logic for different fields
                potential_issues = frappe.db.get_all(
                    child_table,
                    filters={
                        "parenttype": "Issue",
                        "parentfield": field,
                        child_field: ["in", values]
                    },
                    fields=["parent", child_field]
                )
                
                if field == 'custom_users_assigned':
                    # For user assignment: need ALL specified users to be assigned (AND logic)
                    issue_user_counts = {}
                    for link in potential_issues:
                        if link.parent not in issue_user_counts:
                            issue_user_counts[link.parent] = set()
                        issue_user_counts[link.parent].add(link.user_assigned)
                    
                    # Find issues that have all required users assigned
                    required_users_set = set(values)
                    for issue_name, assigned_users in issue_user_counts.items():
                        if required_users_set.issubset(assigned_users):
                            issue_names.add(issue_name)
        
        elif operator == 'equals' or operator == 'is':
            # Issues that have the exact value
            child_links = frappe.db.get_all(
                child_table,
                filters={
                    "parenttype": "Issue",
                    "parentfield": field,
                    child_field: values[0] if values else ""
                },
                fields=["parent"]
            )
            issue_names.update([link.parent for link in child_links])
        
        elif operator == 'not_in':
            # Issues that do NOT have the specified values
            all_issues = frappe.db.get_all(
                "Issue",
                fields=["name"]
            )
            
            # Get all issues that have ANY of the specified values
            issues_with_any_values = frappe.db.get_all(
                child_table,
                filters={
                    "parenttype": "Issue",
                    "parentfield": field,
                    child_field: ["in", values]
                },
                fields=["parent"]
            )
            
            issues_with_values_set = {link.parent for link in issues_with_any_values}
            
            # Return all issues except those that have any of the specified values
            issue_names.update([
                issue.name for issue in all_issues 
                if issue.name not in issues_with_values_set
            ])
        
        if issue_names:
            issue_names_sets.append(issue_names)
        

    # Intersect all sets (AND operation between different child filters)
    print("issue_names_sets : ---------",issue_names_sets)
    if not issue_names_sets:
        return None
    
    result = issue_names_sets[0]
    
    for i, issue_set in enumerate(issue_names_sets[1:], 2):
        result = result.intersection(issue_set)
    
    final_result = list(result)
    
    return final_result


def get_issues_by_tag_filters(tag_filters):
    """
    Get issue names that match tag filters
    Returns None if no tag filters, empty list if no matches, list of names if matches found
    """
    if not tag_filters:
        return None
    
    issue_names_sets = []
    
    for i, tag_filter in enumerate(tag_filters):
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
        
        if operator == 'has':
            # Issues that have ANY of the specified tags (A OR B OR C)
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
            # Issues that have ALL of the specified tags (A AND B AND C)
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
            # Issues that do NOT have ANY of the specified tags (NOT A AND NOT B)
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
    
    for i, issue_set in enumerate(issue_names_sets[1:], 2):
        result = result.intersection(issue_set)
    
    final_result = list(result)
    
    return final_result


@frappe.whitelist()
def get_issues_with_assignments(limit_page_length=10, limit_start=0, filters=None, order_by="creation desc"):
    """
    Get issues list with custom_users_assigned child table data
    Enhanced to handle complex filter objects from frontend and support advanced sorting
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Process and validate order_by parameter
        if isinstance(order_by, str) and order_by.startswith('[') and order_by.endswith(']'):
            # Handle JSON string input from frontend
            try:
                order_by = json.loads(order_by)
            except:
                order_by = "creation desc"
        
        processed_order_by = process_order_by(order_by)
        validated_order_by = validate_and_clean_order_by(processed_order_by)
        
        
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
            "description",
            "communications",
            "custom_assigned_csm_team"
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
                    return []
        
        # Handle child table filters separately (since they are in child tables)
        child_filters = get_child_table_filters(filters)
        issue_names_from_child_tables = None
        
        if child_filters:
            issue_names_from_child_tables = get_issues_by_child_table_filters(child_filters)
            if issue_names_from_child_tables is not None:
                if len(issue_names_from_child_tables) == 0:
                    return []
        
        # Combine all issue name restrictions
        final_issue_names = None
        if issue_names_from_tags is not None and issue_names_from_child_tables is not None:
            # Both filters exist - intersect them
            final_issue_names = list(set(issue_names_from_tags).intersection(set(issue_names_from_child_tables)))
        elif issue_names_from_tags is not None:
            final_issue_names = issue_names_from_tags
        elif issue_names_from_child_tables is not None:
            final_issue_names = issue_names_from_child_tables
        
        # Apply combined name filter if needed
        if final_issue_names is not None:
            if len(final_issue_names) == 0:
                return []
            else:
                processed_filters['name'] = ['in', final_issue_names]
        
        # Get issues using frappe.get_list with enhanced filter handling
        
        if or_filters:
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters=processed_filters,
                or_filters=or_filters,
                order_by=validated_order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start
            )
        else:
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                filters=processed_filters,
                order_by=validated_order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start
            )
        
        
        # Get latest communications for all issues in batch
        issue_names = [issue.name for issue in issues]
        latest_communications = get_latest_communications(issue_names)
        
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
            
            # Add latest communication data
            issue["latest_communication"] = latest_communications.get(issue.name)
        
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
            "description",
            "communications",
            "custom_assigned_csm_team"
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
        
        # Process and validate order_by parameter
        if isinstance(order_by, str) and order_by.startswith('[') and order_by.endswith(']'):
            try:
                order_by = json.loads(order_by)
            except:
                order_by = "creation desc"
        
        processed_order_by = process_order_by(order_by)
        validated_order_by = validate_and_clean_order_by(processed_order_by)
        
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
                "description",
                "custom_assigned_csm_team"
            ]
            
            # Get issues using frappe.get_list to respect permissions
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                or_filters=or_filters,
                order_by=validated_order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
            
            # Get latest communications and unseen counts for all issues in batch
            issue_names = [issue.name for issue in issues]
            latest_communications = get_latest_communications(issue_names)
            
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
                
                issue["latest_communication"] = latest_communications.get(issue.name)
            
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
        
        # Process and validate order_by parameter
        if isinstance(order_by, str) and order_by.startswith('[') and order_by.endswith(']'):
            try:
                order_by = json.loads(order_by)
            except:
                order_by = "creation desc"
        
        processed_order_by = process_order_by(order_by)
        validated_order_by = validate_and_clean_order_by(processed_order_by)
        
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
        
        # Handle child table filters separately (since they are in child tables)
        child_filters = get_child_table_filters(filters)

        issue_names_from_child_tables = None
        
        if child_filters:
            issue_names_from_child_tables = get_issues_by_child_table_filters(child_filters)
            if issue_names_from_child_tables is not None:
                if len(issue_names_from_child_tables) == 0:
                    return []
        
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
            "description",
            "communications",
            "custom_assigned_csm_team"
        ]
        
        # Combine all issue name restrictions
        final_issue_names = None
        if issue_names_from_tags is not None and issue_names_from_child_tables is not None:
            # Both filters exist - intersect them
            final_issue_names = list(set(issue_names_from_tags).intersection(set(issue_names_from_child_tables)))
        elif issue_names_from_tags is not None:
            final_issue_names = issue_names_from_tags
        elif issue_names_from_child_tables is not None:
            final_issue_names = issue_names_from_child_tables
        
        # Build filters based on stat type
        if stat_type == "team_tickets":
            # All issues user can see with additional filters
            combined_filters = additional_filters.copy()
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return []  # No issues match filters
                combined_filters['name'] = ['in', final_issue_names]

            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=validated_order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    order_by=validated_order_by,
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
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return []
                combined_filters['name'] = ['in', final_issue_names]
            
            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=validated_order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    order_by=validated_order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
        
        elif stat_type == "response_tickets":
            # Issues awaiting customer response (custom_is_response_awaited = 1)
            combined_filters = additional_filters.copy()
            combined_filters["custom_is_response_awaited"] = 1
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return []
                combined_filters['name'] = ['in', final_issue_names]
            
            if additional_or_filters:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    or_filters=additional_or_filters,
                    order_by=validated_order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
            else:
                issues = frappe.get_list(
                    "Issue",
                    fields=fields,
                    filters=combined_filters,
                    order_by=validated_order_by,
                    limit_page_length=limit_page_length,
                    limit_start=limit_start,
                    ignore_permissions=False
                )
        
        else:
            # Default to all issues
            issues = frappe.get_list(
                "Issue",
                fields=fields,
                order_by=validated_order_by,
                limit_page_length=limit_page_length,
                limit_start=limit_start,
                ignore_permissions=False
            )
        
        # Get latest communications for all issues in batch
        issue_names = [issue.name for issue in issues]
        latest_communications ,unread_count= get_latest_communications(issue_names)
        
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
            
            # Add latest communication data
            issue["latest_communication"] = latest_communications.get(issue.name)
            issue["unread_count"] = unread_count

        
        
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
        # Validate stat_type parameter
        if not stat_type:
            frappe.throw(_("stat_type parameter is required"))
        
        valid_stat_types = ["team_tickets", "assigned_to_me", "open_tickets", "actionable_tickets", "response_tickets"]
        if stat_type not in valid_stat_types:
            frappe.throw(_("Invalid stat_type: {0}. Valid types are: {1}").format(stat_type, ', '.join(valid_stat_types)))
        
        # Handle additional filters from frontend
        if filters is None:
            filters = []
        elif isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except:
                filters = []
        
        # Process additional filters with error handling
        try:
            additional_filters, additional_or_filters = process_filter_list(filters)
        except Exception as filter_error:
            additional_filters, additional_or_filters = {}, []
        
        # Handle tag filters from additional filters with error handling
        try:
            tag_filters = get_tag_filters(filters)
            issue_names_from_tags = None
            
            if tag_filters:
                issue_names_from_tags = get_issues_by_tag_filters(tag_filters)
                if issue_names_from_tags is not None:
                    if len(issue_names_from_tags) == 0:
                        return 0  # No issues match tag filters
        except Exception as tag_error:
            issue_names_from_tags = None
        
        # Handle child table filters with error handling
        try:
            child_filters = get_child_table_filters(filters)
            issue_names_from_child_tables = None
            
            if child_filters:
                issue_names_from_child_tables = get_issues_by_child_table_filters(child_filters)
                if issue_names_from_child_tables is not None:
                    if len(issue_names_from_child_tables) == 0:
                        return 0  # No issues match child table filters
        except Exception as child_error:
            issue_names_from_child_tables = None
        
        # Combine all issue name restrictions
        final_issue_names = None
        if issue_names_from_tags is not None and issue_names_from_child_tables is not None:
            # Both filters exist - intersect them
            final_issue_names = list(set(issue_names_from_tags).intersection(set(issue_names_from_child_tables)))
            if len(final_issue_names) == 0:
                return 0
        elif issue_names_from_tags is not None:
            final_issue_names = issue_names_from_tags
        elif issue_names_from_child_tables is not None:
            final_issue_names = issue_names_from_child_tables
        
        # Get current user
        current_user = frappe.session.user
        
        if stat_type == "team_tickets":
            # All issues user can see with additional filters
            combined_filters = additional_filters.copy()
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return 0  # No issues match filters
                combined_filters['name'] = ['in', final_issue_names]
            
            try:
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
            except Exception as db_error:
                return 0
        
        elif stat_type == "assigned_to_me":
            # Get all issues first, then filter by assignment
            try:
                all_issues = frappe.get_list(
                    "Issue",
                    fields=["name"],
                    limit_page_length=0,
                    ignore_permissions=False
                )
                
                if all_issues:
                    issue_names = [issue.name for issue in all_issues]
                    
                    # Check if Team User Assignment table exists
                    if not frappe.db.table_exists("Team User Assignment"):
                        return 0
                    
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
            except Exception as db_error:
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
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return 0
                combined_filters['name'] = ['in', final_issue_names]
            
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
            
            # Apply combined filtering if needed
            if final_issue_names is not None:
                if len(final_issue_names) == 0:
                    return 0
                combined_filters['name'] = ['in', final_issue_names]
            
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
            try:
                all_issues = frappe.get_list(
                    "Issue",
                    limit_page_length=0,
                    as_list=True,
                    ignore_permissions=False
                )
                return len(all_issues)
            except Exception as db_error:
                return 0
        
    except Exception as e:
        error_message = str(e)
        frappe.log_error(f"Error in get_stat_filter_count: {error_message}")
        
        # Return 0 instead of throwing to avoid frontend errors
        return 0


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
def search_user_groups(search_query="", limit=10):
    """
    Search User Groups for CSM Team autocomplete in filters
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            return []
        
        search_query = search_query.strip()
        
        # Get user groups using frappe.get_list to respect permissions
        or_filters = [
            ["name", "like", f"%{search_query}%"]
        ]
        
        user_groups = frappe.get_list(
            "User Group",
            fields=["name"],
            or_filters=or_filters,
            order_by="name asc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        # Format results for frontend
        results = []
        for group in user_groups:
            # Get member count for display
            member_count = frappe.db.count(
                "User Group Member",
                filters={"parent": group.name}
            )
            
            results.append({
                "value": group.name,
                "label": group.name,
                "subtitle": f"{member_count} member(s)" if member_count > 0 else "Empty group",
                "type": "user_group"
            })
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in search_user_groups: {str(e)}")
        frappe.throw(_("Failed to search user groups: {0}").format(str(e)))


@frappe.whitelist()
def search_contacts(search_query="", limit=10):
    """
    Search contacts for autocomplete in filters
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            return []
        
        search_query = search_query.strip()
        
        # Get contacts using frappe.get_list to respect permissions
        or_filters = [
            ["name", "like", f"%{search_query}%"],
            ["first_name", "like", f"%{search_query}%"],
            ["last_name", "like", f"%{search_query}%"],
            ["email_id", "like", f"%{search_query}%"]
        ]
        
        contacts = frappe.get_list(
            "Contact",
            fields=["name", "first_name", "last_name", "email_id", "company_name"],
            or_filters=or_filters,
            order_by="first_name asc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        # Format results for frontend
        results = []
        for contact in contacts:
            display_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
            if not display_name:
                display_name = contact.name
            
            subtitle = contact.email_id or contact.company_name or contact.name
            
            results.append({
                "value": contact.name,
                "label": display_name,
                "subtitle": subtitle,
                "type": "contact"
            })
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in search_contacts: {str(e)}")
        frappe.throw(_("Failed to search contacts: {0}").format(str(e)))


@frappe.whitelist()
def get_sortable_columns():
    """
    Get list of sortable columns with their display labels for the frontend
    """
    try:
        columns = [
            {"field": "name", "label": "Issue ID", "type": "string"},
            {"field": "subject", "label": "Subject", "type": "string"},
            {"field": "status", "label": "Status", "type": "string"},
            {"field": "priority", "label": "Priority", "type": "string"},
            {"field": "raised_by", "label": "Raised By", "type": "string"},
            {"field": "customer", "label": "Customer", "type": "string"},
            {"field": "project", "label": "Project", "type": "string"},
            {"field": "issue_type", "label": "Issue Type", "type": "string"},
            {"field": "creation", "label": "Created On", "type": "datetime"},
            {"field": "modified", "label": "Modified On", "type": "datetime"},
            {"field": "owner", "label": "Owner", "type": "string"},
            {"field": "first_responded_on", "label": "First Response", "type": "datetime"},
            {"field": "resolution_time", "label": "Resolution Time", "type": "duration"}
        ]
        return columns
    except Exception as e:
        frappe.log_error(f"Error in get_sortable_columns: {str(e)}")
        frappe.throw(_("Failed to get sortable columns: {0}").format(str(e)))


@frappe.whitelist()
def search_leads(search_query="", limit=10):
    """
    Search leads for autocomplete in filters
    """
    try:
        limit = int(limit)
        
        if not search_query or len(search_query.strip()) < 1:
            return []
        
        search_query = search_query.strip()
        
        # Get leads using frappe.get_list to respect permissions
        or_filters = [
            ["name", "like", f"%{search_query}%"],
            ["lead_name", "like", f"%{search_query}%"],
            ["email_id", "like", f"%{search_query}%"],
            ["company_name", "like", f"%{search_query}%"]
        ]
        
        leads = frappe.get_list(
            "Lead",
            fields=["name", "lead_name", "email_id", "company_name", "status"],
            or_filters=or_filters,
            order_by="lead_name asc",
            limit_page_length=limit,
            ignore_permissions=False
        )
        
        # Format results for frontend
        results = []
        for lead in leads:
            display_name = lead.lead_name or lead.name
            subtitle_parts = []
            
            if lead.email_id:
                subtitle_parts.append(lead.email_id)
            if lead.company_name:
                subtitle_parts.append(lead.company_name)
            if lead.status:
                subtitle_parts.append(f"Status: {lead.status}")
            
            subtitle = " • ".join(subtitle_parts) if subtitle_parts else lead.name
            
            results.append({
                "value": lead.name,
                "label": display_name,
                "subtitle": subtitle,
                "type": "lead"
            })
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in search_leads: {str(e)}")
        frappe.throw(_("Failed to search leads: {0}").format(str(e)))


@frappe.whitelist()
def get_issue_communications(issue_name, limit=5):
    """
    Get latest communications for a specific issue
    Returns latest communications with full content for detailed view
    """
    try:
        limit = int(limit)
        
        if not issue_name:
            frappe.throw(_("Issue name is required"))
        
        # Check if issue exists and user has permission
        if not frappe.db.exists("Issue", issue_name):
            frappe.throw(_("Issue not found"))
            
        # Get communications for the issue
        communications = frappe.db.sql("""
            SELECT 
                name,
                subject,
                content,
                sent_or_received,
                creation,
                modified,
                sender,
                recipients,
                seen,
                communication_medium,
                communication_type
            FROM `tabCommunication`
            WHERE 
                reference_doctype = 'Issue'
                AND reference_name = %s
                AND communication_type = 'Communication'
                AND content IS NOT NULL
                AND content != ''
            ORDER BY creation DESC
            LIMIT %s
        """, [issue_name, limit], as_dict=True)
        
        # Process communications to clean content and add metadata
        processed_communications = []
        for comm in communications:
            processed_communications.append({
                'name': comm.name,
                'subject': comm.subject or 'No Subject',
                'content': comm.content,
                'sent_or_received': comm.sent_or_received,
                'creation': comm.creation,
                'modified': comm.modified,
                'sender': comm.sender,
                'recipients': comm.recipients,
                'seen': comm.seen,
                'communication_medium': comm.communication_medium,
                'communication_type': comm.communication_type,
                'formatted_date': comm.creation.strftime("%Y-%m-%d %H:%M:%S") if comm.creation else "",
                'relative_time': get_relative_time(comm.creation) if comm.creation else ""
            })
        
        return processed_communications
        
    except Exception as e:
        frappe.log_error(f"Error in get_issue_communications: {str(e)}")
        frappe.throw(_("Failed to fetch communications: {0}").format(str(e)))


def get_relative_time(datetime_obj):
    """
    Get relative time string like '2 hours ago', '3 days ago', etc.
    """
    try:
        from datetime import datetime, timedelta
        
        if not datetime_obj:
            return ""
            
        now = datetime.now()
        
        # Convert to datetime if it's a date
        if hasattr(datetime_obj, 'date') and not hasattr(datetime_obj, 'hour'):
            datetime_obj = datetime.combine(datetime_obj, datetime.min.time())
            
        diff = now - datetime_obj
        
        if diff.days > 0:
            if diff.days == 1:
                return "1 day ago"
            elif diff.days < 30:
                return f"{diff.days} days ago"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            else:
                years = diff.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
            
    except Exception as e:
        frappe.log_error(f"Error in get_relative_time: {str(e)}")
        return ""


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