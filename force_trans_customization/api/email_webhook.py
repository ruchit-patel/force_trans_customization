# webhook_handler.py
# 
# Email Webhook Handler for AWS SES with Support Issue Creation
# 
# This module processes incoming emails via webhook and:
# 1. Creates Communication records from email data
# 2. Automatically creates Support Issues from communications
# 3. Links communications to existing issues when appropriate
# 4. Handles email attachments and file uploads
# 5. Attempts to match emails to existing customers and contacts
#
# Key Features:
# - Automatic issue creation from incoming emails
# - Issue thread detection (links replies to existing issues)
# - Customer/Contact matching by email address
# - Attachment processing and file storage
# - Support for both structured and raw email data
#
import frappe
import json
import base64
import hashlib
import mimetypes
import email
import re
from frappe import _
from frappe.utils import now_datetime, strip_html_tags, cstr, get_datetime, today, nowtime
from frappe.email.doctype.email_account.email_account import EmailAccount
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header


@frappe.whitelist(methods=["POST"])
def test():
    """
    Webhook handler for AWS SES emails processed by Lambda
    Maps the email data to Frappe's email structure
    """
    try:
        # Get the JSON data from the request
        email_data = frappe.request.get_data(as_text=True)
        if not email_data:
            frappe.throw(_("No email data received"))
        
        email_json = json.loads(email_data)
        
        # Process the email
        communication = process_ses_email(email_json)
        
        # Get the linked support issue if created
        support_issue = None
        if communication and hasattr(communication, 'reference_doctype') and communication.reference_doctype == "Issue":
            support_issue = getattr(communication, 'reference_name', None)
        
        return {
            "status": "success",
            "message": "Email processed successfully",
            "communication": communication.name if communication else None,
            "support_issue": support_issue
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Error processing SES webhook: {str(e)}\nData: {email_data}",
            title="SES Webhook Error"
        )
        frappe.response["http_status_code"] = 500
        return {
            "status": "error",
            "message": str(e)
        }


def process_ses_email(email_data):
    """
    Process the SES email data and create Communication record
    """
    try:
        # Check if raw email content is provided
        if "raw_email" in email_data:
            # Parse the raw email to extract all components
            return process_raw_email(email_data["raw_email"])
        
        # Extract email details from structured data
        message_id = email_data.get("message_id") 
        timestamp = email_data.get("timestamp")
        from_email = email_data.get("from_email")
        to_emails = email_data.get("to_emails", [])
        subject = email_data.get("subject", "")
        body_text = email_data.get("body_text", "")
        body_html = email_data.get("body_html", "")
        attachments = email_data.get("attachments", [])
        headers = email_data.get("headers", {})
        
        # Clean up body text (remove escape characters)
        body_text = body_text.replace("\\r\\n", "\n").replace("\\n", "\n")
        
        # Determine the primary recipient (first to_email)
        primary_recipient = to_emails[0] if to_emails else ""
        
        # Find matching Email Account
        email_account = find_matching_email_account(primary_recipient, to_emails)
        
        # Create Communication record
        communication = create_communication_record(
            message_id=message_id,
            timestamp=timestamp,
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            headers=headers,
            email_account=email_account
        )
        
        # Process attachments if any
        if attachments:
            process_attachments(communication, attachments, email_data)
        
        # Link to relevant documents if possible
        link_communication_to_documents(communication)
        
        return communication
        
    except Exception as e:
        frappe.log_error(
            message=f"Error in process_ses_email: {str(e)}",
            title="SES Email Processing Error"
        )
        raise


def process_raw_email(raw_email_content):
    """
    Process raw email content and extract all components including attachments
    """
    try:
        # Parse the raw email
        msg = email.message_from_string(raw_email_content)
        
        # Extract basic email info
        message_id = msg.get('Message-ID', '')
        subject = decode_email_header(msg.get('Subject', ''))
        from_email = msg.get('From', '')
        to_emails = [addr.strip() for addr in msg.get('To', '').split(',')]
        date_header = msg.get('Date', '')
        
        # Extract email body
        body_text = ""
        body_html = ""
        attachments = []
        
        # Process multipart message
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip multipart containers
                if content_type.startswith('multipart/'):
                    continue
                
                # Handle text parts
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body_text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                    else:
                        body_text = str(payload)
                elif content_type == 'text/html' and 'attachment' not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body_html = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                    else:
                        body_html = str(payload)
                
                # Handle attachments
                elif 'attachment' in content_disposition or part.get_filename():
                    filename = part.get_filename()
                    if filename:
                        filename = decode_email_header(filename)
                        attachment_data = part.get_payload(decode=True)
                        
                        attachments.append({
                            'filename': filename,
                            'content_type': content_type,
                            'content': attachment_data,
                            'size': len(attachment_data) if attachment_data else 0
                        })
        else:
            # Single part message
            content_type = msg.get_content_type()
            if content_type == 'text/plain':
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_text = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                else:
                    body_text = str(payload)
            elif content_type == 'text/html':
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body_html = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                else:
                    body_html = str(payload)
        
        # Find matching Email Account
        primary_recipient = to_emails[0] if to_emails else ""
        email_account = find_matching_email_account(primary_recipient, to_emails)
        
        # Create Communication record
        communication = create_communication_record(
            message_id=message_id,
            timestamp=date_header,
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            headers=dict(msg.items()),
            email_account=email_account
        )
        
        # Process attachments
        if attachments:
            process_email_attachments(communication, attachments)
        
        # Link to relevant documents if possible
        link_communication_to_documents(communication)
        
        return communication
        
    except Exception as e:
        frappe.log_error(
            message=f"Error in process_raw_email: {str(e)}",
            title="Raw Email Processing Error"
        )
        raise


def decode_email_header(header_value):
    """
    Decode email header that might be encoded
    """
    if not header_value:
        return ""
    
    try:
        decoded_header = decode_header(header_value)
        decoded_string = ""
        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string
    except Exception:
        return str(header_value)


def find_matching_email_account(primary_recipient, all_recipients):
    """
    Find the Email Account that matches the recipient
    """
    email_account = None
    
    # First try to find by primary recipient
    if primary_recipient:
        email_account = frappe.db.get_value(
            "Email Account", 
            {"email_id": primary_recipient, "enable_incoming": 1}, 
            "name"
        )
    
    # If not found, try other recipients
    if not email_account:
        for recipient in all_recipients:
            email_account = frappe.db.get_value(
                "Email Account", 
                {"email_id": recipient, "enable_incoming": 1}, 
                "name"
            )
            if email_account:
                break
    
    # If still not found, try to find a default or support email account
    if not email_account:
        email_account = frappe.db.get_value(
            "Email Account", 
            {"enable_incoming": 1, "default_incoming": 1}, 
            "name"
        )
    
    return email_account


def create_communication_record(message_id, timestamp, from_email, to_emails, 
                              subject, body_text, body_html, headers, email_account):
    """
    Create a Communication record similar to how Frappe handles IMAP/POP emails
    """
    
    # Parse sender name and email
    sender_name, sender_email = parse_email_address(from_email)
    
    # Create the communication document
    communication = frappe.new_doc("Communication")
    communication.communication_type = "Communication"
    communication.communication_medium = "Email"
    communication.sent_or_received = "Received"
    communication.subject = subject
    communication.sender = sender_email
    communication.sender_full_name = sender_name or sender_email
    
    # Set recipients
    communication.recipients = ", ".join(to_emails)
    
    # Set content - prefer HTML over text
    if body_html and body_html.strip():
        communication.content = body_html
        communication.text_content = strip_html_tags(body_html)
    else:
        communication.content = body_text.replace("\n", "<br>") if body_text else ""
        communication.text_content = body_text or ""
    
    # Set timestamps
    if timestamp:
        try:
            # Try to parse different timestamp formats
            if isinstance(timestamp, str) and 'T' in timestamp:
                # ISO 8601 format
                communication.communication_date = parse_iso_datetime(timestamp)
            else:
                # Email date header format
                communication.communication_date = parse_email_date(timestamp)
        except Exception as e:
            frappe.log_error(f"Error parsing timestamp {timestamp}: {str(e)}")
            communication.communication_date = now_datetime()
    else:
        communication.communication_date = now_datetime()
    
    # Set email account
    if email_account:
        communication.email_account = email_account
    
    # Set message ID for deduplication
    communication.message_id = message_id
    
    # Add email headers as JSON
    if headers:
        communication.email_headers = json.dumps(headers)
    
    # Set status
    communication.status = "Open"
    communication.read_by_recipient = 0
    
    # Save the communication
    communication.insert(ignore_permissions=True)
    
    # Commit the transaction
    frappe.db.commit()
    
    # Create support issue after communication is saved
    support_issue = create_support_issue_from_communication(communication, sender_email, sender_name, to_emails)
    
    return communication


def parse_email_date(date_string):
    """
    Parse email date header to Frappe datetime format
    """
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        frappe.log_error(f"Error parsing email date {date_string}: {str(e)}")
        return now_datetime()


def parse_iso_datetime(iso_string):
    """
    Parse ISO 8601 datetime string to Frappe datetime format
    """
    from datetime import datetime
    
    try:
        # Remove 'Z' and handle microseconds
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        
        # Handle different ISO 8601 formats
        if '+' in iso_string or iso_string.endswith('Z'):
            # With timezone
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        else:
            # Without timezone, assume UTC
            if '.' in iso_string:
                # With microseconds
                dt = datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S.%f')
            else:
                # Without microseconds
                dt = datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S')
        
        # Convert to Frappe's expected format
        return dt.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        frappe.log_error(f"Error parsing datetime {iso_string}: {str(e)}")
        return now_datetime()


def parse_email_address(email_string):
    """
    Parse email address to extract name and email
    """
    if not email_string:
        return None, None
    
    import re
    
    # Pattern to match "Name <email@domain.com>"
    match = re.match(r'^(.+?)\s*<(.+?)>$', email_string.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return name, email
    else:
        # If no name is found, just return the email
        return None, email_string.strip()


def process_email_attachments(communication, attachments):
    """
    Process email attachments and save them as File documents
    """
    for attachment in attachments:
        try:
            filename = attachment.get("filename")
            content_type = attachment.get("content_type")
            content = attachment.get("content")
            size = attachment.get("size", 0)
            
            if content and filename:
                # Create File document
                file_doc = create_file_document(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    communication=communication
                )
                
                # Add attachment to communication
                communication.append("attachments", {
                    "file_url": file_doc.file_url,
                    "file_name": filename
                })
                
                frappe.log_error(
                    message=f"Successfully processed attachment: {filename} for communication: {communication.name}",
                    title="Attachment Processed"
                )
        
        except Exception as e:
            frappe.log_error(
                message=f"Error processing attachment {filename}: {str(e)}",
                title="Attachment Processing Error"
            )
    
    # Save communication with attachments
    if communication.attachments:
        communication.save(ignore_permissions=True)
        frappe.db.commit()


def process_attachments(communication, attachments, email_data):
    """
    Process email attachments and save them as File documents
    Legacy function - keeping for backward compatibility
    """
    s3_bucket = email_data.get("s3_bucket")
    s3_key = email_data.get("s3_key")
    
    for attachment in attachments:
        try:
            filename = attachment.get("filename")
            content_type = attachment.get("content_type")
            size = attachment.get("size", 0)
            
            # If attachment content is provided directly
            if "content" in attachment:
                content = attachment["content"]
                if isinstance(content, str):
                    # Assume base64 encoded
                    file_content = base64.b64decode(content)
                else:
                    file_content = content
            else:
                # If stored in S3, you might need to fetch it
                file_content = fetch_attachment_from_s3(s3_bucket, s3_key, filename)
            
            # Create File document
            if file_content and filename:
                file_doc = create_file_document(
                    filename=filename,
                    content=file_content,
                    content_type=content_type,
                    communication=communication
                )
                
                # Link attachment to communication
                communication.append("attachments", {
                    "file_url": file_doc.file_url,
                    "file_name": filename
                })
        
        except Exception as e:
            frappe.log_error(
                message=f"Error processing attachment {filename}: {str(e)}",
                title="Attachment Processing Error"
            )
    
    # Save communication with attachments
    if communication.attachments:
        communication.save(ignore_permissions=True)
        frappe.db.commit()


def fetch_attachment_from_s3(bucket, key, filename):
    """
    Fetch attachment from S3 - implement based on your AWS setup
    """
    try:
        import boto3
        s3_client = boto3.client('s3')
        
        # This would fetch the original email from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        email_content = response['Body'].read()
        
        # Parse the email to extract specific attachment
        msg = email.message_from_bytes(email_content)
        
        for part in msg.walk():
            if part.get_filename() == filename:
                return part.get_payload(decode=True)
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error fetching from S3: {str(e)}")
        return None


def create_file_document(filename, content, content_type, communication):
    """
    Create a File document for the attachment
    """
    try:
        # Create file document
        file_doc = frappe.new_doc("File")
        file_doc.file_name = filename
        
        # Set content type
        if content_type:
            file_doc.content_type = content_type
        else:
            file_doc.content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        # Link to communication
        file_doc.attached_to_doctype = "Communication"
        file_doc.attached_to_name = communication.name
        file_doc.folder = "Home/Attachments"
        
        # Save the file content
        if isinstance(content, bytes):
            file_doc.content = content
        else:
            file_doc.content = str(content).encode()
        
        # Insert the file document
        file_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return file_doc
        
    except Exception as e:
        frappe.log_error(f"Error creating file document for {filename}: {str(e)}")
        raise


def link_communication_to_documents(communication):
    """
    Try to link the communication to relevant documents based on email content
    """
    try:
        # Extract potential document references from subject and content
        subject = communication.subject or ""
        content = communication.text_content or ""
        
        search_text = f"{subject} {content}".lower()
        
        # Look for document patterns
        patterns = {
            "Customer": [r"customer", r"client"],
            "Lead": [r"lead", r"inquiry", r"enquiry"],
            "Issue": [r"issue", r"problem", r"bug", r"support"],
            "Project": [r"project", r"proj"],
            "Sales Order": [r"so-", r"sales order", r"order"],
            "Purchase Order": [r"po-", r"purchase order"],
            "Quotation": [r"quot-", r"quotation", r"quote"],
        }
        
        for doctype, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in search_text:
                    # Try to find and link the document
                    break
    
    except Exception as e:
        frappe.log_error(f"Error linking communication: {str(e)}")


@frappe.whitelist()
def test_webhook():
    """
    Test endpoint to verify webhook is working
    """
    return {"status": "success", "message": "Webhook is working"}


def validate_webhook_signature(payload, signature, secret):
    """
    Validate webhook signature for security (optional)
    """
    expected_signature = hashlib.sha256(
        f"{secret}{payload}".encode()
    ).hexdigest()
    
    return signature == expected_signature


def create_support_issue_from_communication(communication, sender_email, sender_name, to_emails):
    """
    Create a Support Issue from the Communication record
    """
    try:
        # Check if an issue already exists for this email thread
        existing_issue = find_existing_issue(communication.subject, sender_email)
        if existing_issue:
            # Link the communication to the existing issue
            link_communication_to_issue(communication, existing_issue)

            # Update issue status based on incoming customer reply
            update_issue_status_on_customer_reply(existing_issue)
            return existing_issue
        
        # Create a new Issue
        issue = frappe.new_doc("Issue")
        
        # Set basic fields
        issue.subject = communication.subject or "Support Request"
        issue.raised_by = sender_email
        issue.description = communication.text_content or communication.content
        issue.status = "New"
        issue.priority = get_default_priority()
        issue.issue_type = get_default_issue_type()
        
        # Set dates
        issue.opening_date = today()
        issue.opening_time = nowtime()
        
        # Try to find customer from email
        customer = find_customer_by_email(sender_email)
        if customer:
            issue.customer = customer
            issue.customer_name = frappe.db.get_value("Customer", customer, "customer_name")
        
        # Try to find contact from email
        contact = find_contact_by_email(sender_email)
        if contact:
            issue.contact = contact
        
        # Set email account
        if communication.email_account:
            issue.email_account = communication.email_account
        
        # Set company (get default or from email account)
        issue.company = get_default_company(communication.email_account)
        
        # Auto-assign to user group based on recipient email
        user_group = get_user_group_by_recipient_email(to_emails)
        if user_group:
            issue.custom_assigned_csm_team = user_group
        
        # Save the issue
        issue.insert(ignore_permissions=True)
        
        # Link the communication to the issue
        link_communication_to_issue(communication, issue.name)
        
        # Commit the transaction
        frappe.db.commit()
        
        frappe.log_error(
            message=f"Successfully created support issue {issue.name} from communication {communication.name}",
            title="Support Issue Created"
        )
        
        return issue
        
    except Exception as e:
        frappe.log_error(
            message=f"Error creating support issue from communication {communication.name}: {str(e)}",
            title="Support Issue Creation Error"
        )
        return None


def find_existing_issue(subject, sender_email):
    """
    Find an existing issue with similar subject from the same sender
    """
    try:
        # Clean subject for matching (remove Re:, Fwd:, etc.)
        clean_subject = re.sub(r'^(Re:|Fwd?:|RE:|FWD?:)\s*', '', subject, flags=re.IGNORECASE).strip()
        
        # Look for existing issues with similar subject from same sender
        issues = frappe.get_list(
            "Issue",
            filters={
                "raised_by": sender_email,
                "status": ["not in", ["Closed", "Resolved"]]
            },
            or_filters=[
                {"subject": ["like", f"%{clean_subject}%"]},
                {"subject": ["like", f"%{subject}%"]}
            ],
            order_by="creation desc",
            limit=1,
            pluck="name"
        )
        
        return issues[0] if issues else None
        
    except Exception as e:
        frappe.log_error(f"Error finding existing issue: {str(e)}")
        return None


def link_communication_to_issue(communication, issue_name):
    """
    Link the communication to the issue
    """
    try:
        # Set reference fields if they exist
        if hasattr(communication, 'reference_doctype'):
            communication.reference_doctype = "Issue"
        if hasattr(communication, 'reference_name'):
            communication.reference_name = issue_name
        
        communication.save(ignore_permissions=True)
        
        frappe.log_error(
            message=f"Linked communication {communication.name} to issue {issue_name}",
            title="Communication Linked"
        )
        
    except Exception as e:
        frappe.log_error(f"Error linking communication to issue: {str(e)}")


def find_customer_by_email(email):
    """
    Find customer by email address
    """
    try:
        # Try customer primary email
        customer = frappe.db.get_value("Customer", {"email_id": email}, "name")
        if customer:
            return customer
        
        # Try contact email - first find contacts with this email
        contacts = frappe.get_list(
            "Contact Email",
            filters={"email_id": email},
            fields=["parent"],
            pluck="parent"
        )
        
        # For each contact, check if linked to a customer
        for contact_name in contacts:
            customer_links = frappe.get_list(
                "Dynamic Link",
                filters={
                    "parent": contact_name,
                    "link_doctype": "Customer"
                },
                fields=["link_name"],
                limit=1,
                pluck="link_name"
            )
            
            if customer_links:
                return customer_links[0]
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error finding customer by email: {str(e)}")
        return None


def find_contact_by_email(email):
    """
    Find contact by email address
    """
    try:
        # Find contacts with this email address
        contacts = frappe.get_list(
            "Contact Email",
            filters={"email_id": email},
            fields=["parent"],
            limit=1,
            pluck="parent"
        )
        
        return contacts[0] if contacts else None
        
    except Exception as e:
        frappe.log_error(f"Error finding contact by email: {str(e)}")
        return None


def get_default_priority():
    """
    Get default issue priority
    """
    try:
        default_priority = frappe.db.get_value("Issue Priority", {"name": "Medium"}, "name")
        if not default_priority:
            # Get any priority
            default_priority = frappe.db.get_value("Issue Priority", {}, "name")
        return default_priority
    except Exception:
        return None


def get_default_issue_type():
    """
    Get default issue type
    """
    try:
        default_type = frappe.db.get_value("Issue Type", {"name": "General"}, "name")
        if not default_type:
            # Get any issue type
            default_type = frappe.db.get_value("Issue Type", {}, "name")
        return default_type
    except Exception:
        return None


def get_default_company(email_account=None):
    """
    Get default company for the issue
    """
    try:
        # Try to get company from email account
        if email_account:
            company = frappe.db.get_value("Email Account", email_account, "default_company")
            if company:
                return company
        
        # Get default company
        default_company = frappe.db.get_single_value("Global Defaults", "default_company")
        return default_company
        
    except Exception:
        return None


def get_user_group_by_recipient_email(to_emails):
    """
    Map recipient email addresses to user groups for auto-assignment
    Uses the custom_associated_email field from User Group doctype
    """
    try:
        if not to_emails:
            return None
        
        # Check each recipient email against user groups with associated emails
        for email in to_emails:
            email = email.strip().lower()
            
            # Find user group that has this email as associated_email
            user_group = frappe.db.get_value(
                "User Group",
                {"custom_associated_email": email},
                "name"
            )
            
            if user_group:
                frappe.log_error(
                    message=f"Auto-assigned issue to user group: {user_group} based on associated email: {email}",
                    title="User Group Auto-Assignment"
                )
                return user_group
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error mapping email to user group: {str(e)}")
        return None


##will remove this later.. kept it only so we keep in mind that we have option2 .. this method is currently not referenced by any other method
def get_user_group_from_email_account(email_account):
    """
    Alternative method: Get user group from Email Account configuration
    This can be used if you want to configure user groups directly in Email Account doctype
    """
    try:
        if not email_account:
            return None
            
        # Check if Email Account has a custom field for user group mapping
        # You would need to add a custom field 'default_user_group' to Email Account doctype
        user_group = frappe.db.get_value("Email Account", email_account, "default_user_group")
        
        if user_group and frappe.db.exists("User Group", user_group):
            return user_group
            
        return None
        
    except Exception as e:
        frappe.log_error(f"Error getting user group from email account: {str(e)}")
        return None


def update_issue_status_on_customer_reply(issue_name):
    """
    When an incoming customer email is linked to an existing Issue, adjust the Issue status:
    1. If the Issue is in "Waiting on Customer" state -> move to "In Review"
    2. If the Issue is in "In Transit" state -> move to "In Transit Unmanaged"
    Any other state is left unchanged.
    """
    try:
        issue_doc = frappe.get_doc("Issue", issue_name)

        # Perform status transitions only if needed
        if issue_doc.status == "Waiting on Customer":
            new_status = "In Review"
        elif issue_doc.status == "In Transit":
            new_status = "In Transit Unmanaged"
        else:
            return  # No change required

        issue_doc.status = new_status
        issue_doc.save(ignore_permissions=True)

        # Log a comment on the Issue for traceability
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Issue",
            "reference_name": issue_name,
            "content": _(f"Issue status automatically updated to '{new_status}' based on customer reply."),
            "comment_by": "Administrator" if frappe.flags.in_test else frappe.session.user
        }).insert(ignore_permissions=True)

        frappe.log_error(
            message=f"Issue {issue_name} status updated to '{new_status}' after customer reply.",
            title="Issue Status Auto-Update"
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error updating status for Issue {issue_name}: {str(e)}",
            title="Issue Status Update Error"
        )