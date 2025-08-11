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
from frappe.utils import now_datetime, strip_html_tags, cstr, get_datetime, today, nowtime, get_string_between
from frappe.email.doctype.email_account.email_account import EmailAccount
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header

# Thread ID pattern from Frappe's receive.py
THREAD_ID_PATTERN = re.compile(r"(?<=\[)[\w/-]+")


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
        
        # Extract In-Reply-To header for reply detection
        in_reply_to = headers.get('In-Reply-To', '') or headers.get('in-reply-to', '')
        if in_reply_to:
            in_reply_to = get_string_between('<', in_reply_to, '>')
        
        # Clean message_id
        if message_id:
            message_id = get_string_between('<', message_id, '>')
        
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
            email_account=email_account,
            in_reply_to=in_reply_to
        )
        
        # Process attachments if any
        if attachments:
            # Check if HTML content has cid: references and try to match with attachments
            if body_html and "cid:" in body_html:
                attachments = match_cid_references_with_attachments(body_html, attachments)
            
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
                
                # Handle attachments and inline images
                elif 'attachment' in content_disposition or 'inline' in content_disposition or part.get_filename() or part.get('Content-ID'):
                    filename = part.get_filename()
                    content_id = part.get('Content-ID')
                    
                    if filename or content_id:
                        if filename:
                            filename = decode_email_header(filename)
                        else:
                            filename = f"inline_{content_id.strip('<>')}" if content_id else "unnamed_attachment"
                            
                        attachment_data = part.get_payload(decode=True)
                        
                        attachment_info = {
                            'filename': filename,
                            'content_type': content_type,
                            'content': attachment_data,
                            'size': len(attachment_data) if attachment_data else 0
                        }
                        
                        # Add Content-ID for inline images
                        if content_id:
                            attachment_info['content_id'] = content_id.strip('<>')
                            attachment_info['is_inline'] = True
                        else:
                            attachment_info['is_inline'] = False
                            
                        attachments.append(attachment_info)
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
        
        # Extract In-Reply-To header for reply detection
        in_reply_to = msg.get('In-Reply-To', '')
        if in_reply_to:
            in_reply_to = get_string_between('<', in_reply_to, '>')
        
        # Extract message_id properly
        if message_id:
            message_id = get_string_between('<', message_id, '>')
        
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
            email_account=email_account,
            in_reply_to=in_reply_to
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


def match_cid_references_with_attachments(html_content, attachments):
    """
    Extract cid: references from HTML content and match them with attachments
    This version uses both HTML order and attachment metadata for accurate matching
    """
    import re
    
    # Find all cid: references in HTML content with their positions
    cid_pattern = r'src="cid:([^"]+)"'
    cid_matches_with_pos = []
    for match in re.finditer(cid_pattern, html_content):
        cid_matches_with_pos.append({
            'cid': match.group(1),
            'position': match.start(),
            'matched': False
        })
    
    if not cid_matches_with_pos:
        return attachments
    
    # Sort CIDs by their position in HTML (preserves original order)
    cid_matches_with_pos.sort(key=lambda x: x['position'])
    
    # Separate image attachments from other attachments
    inline_images = []
    regular_attachments = []
    
    for attachment in attachments:
        content_type = attachment.get("content_type", "")
        is_inline = attachment.get("is_inline", False)
        
        if is_inline and content_type.startswith("image/"):
            inline_images.append(attachment)
        else:
            regular_attachments.append(attachment)
    
    # If Lambda function provided html_order, use that for sorting
    if inline_images and any(att.get('html_order') is not None for att in inline_images):
        inline_images.sort(key=lambda x: x.get('html_order', 999))
        frappe.log("Using Lambda-provided HTML order for inline images")
    
    # Create updated attachments list
    updated_attachments = []
    
    # Method 1: Try to match by content_id if available (most reliable)
    if inline_images and all(att.get('content_id') for att in inline_images):
        frappe.log("Using content_id matching for inline images")
        
        # Create a map of CID to HTML position
        cid_to_position = {cid_info['cid']: i for i, cid_info in enumerate(cid_matches_with_pos)}
        
        # Sort inline images by their CID's position in HTML
        def get_html_position(attachment):
            cid = attachment.get('content_id', '')
            return cid_to_position.get(cid, 999)
        
        inline_images.sort(key=get_html_position)
        
        # Add sorted inline images
        for attachment in inline_images:
            attachment_copy = attachment.copy()
            attachment_copy["is_inline"] = True
            updated_attachments.append(attachment_copy)
            
            cid = attachment.get('content_id', '')
            frappe.log(f"Matched inline image: CID={cid}, Filename={attachment.get('filename', 'unnamed')}")
    
    # Method 2: Fallback to order-based matching
    else:
        frappe.log("Using order-based matching for inline images")
        
        # Match images to CIDs in order of appearance in HTML
        for i, cid_info in enumerate(cid_matches_with_pos):
            if i < len(inline_images):
                # Match the i-th CID with the i-th image attachment
                attachment_copy = inline_images[i].copy()
                attachment_copy["content_id"] = cid_info['cid']
                attachment_copy["is_inline"] = True
                updated_attachments.append(attachment_copy)
                
                frappe.log(f"Order-matched CID '{cid_info['cid']}' (position {i+1}) with attachment '{attachment_copy.get('filename', 'unnamed')}'")
        
        # Add any remaining image attachments that couldn't be matched to CIDs
        for i in range(len(cid_matches_with_pos), len(inline_images)):
            attachment_copy = inline_images[i].copy()
            attachment_copy["is_inline"] = False  # Treat as regular attachment
            updated_attachments.append(attachment_copy)
    
    # Add regular attachments
    for attachment in regular_attachments:
        attachment_copy = attachment.copy()
        attachment_copy["is_inline"] = False
        updated_attachments.append(attachment_copy)
    
    return updated_attachments

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


def clean_email_content(content):
    """
    Clean up email content by removing excessive newlines and spacing
    """
    if not content:
        return content
    
    # Remove excessive newlines and spacing
    import re
    
    # Replace multiple newlines with single newline
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Replace multiple spaces with single space
    content = re.sub(r' +', ' ', content)
    
    # Remove leading/trailing whitespace from each line
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:  # Only add non-empty lines
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1]:  # Add single empty line between content
            cleaned_lines.append('')
    
    # Join lines back together
    content = '\n'.join(cleaned_lines)
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    return content


def create_communication_record(message_id, timestamp, from_email, to_emails, 
                              subject, body_text, body_html, headers, email_account, in_reply_to=None):
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
    
    # Set content - prefer HTML over text, with cleanup
    if body_html and body_html.strip():
        communication.content = body_html
        # Clean up text content from HTML
        text_content = strip_html_tags(body_html)
        communication.text_content = clean_email_content(text_content)
    else:
        # Clean up plain text content
        cleaned_text = clean_email_content(body_text) if body_text else ""
        communication.content = cleaned_text.replace("\n", "<br>") if cleaned_text else ""
        communication.text_content = cleaned_text or ""
    
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
    
    # Set In-Reply-To for threading (mimicking Frappe's approach)
    if in_reply_to:
        # Check if this is a reply to system-sent mail
        if frappe.local.site in in_reply_to:
            # Find parent communication by message_id
            parent_communication = find_parent_communication(in_reply_to)
            if parent_communication:
                communication.in_reply_to = parent_communication.name
    
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
    Convert to system timezone
    """
    try:
        from email.utils import parsedate_to_datetime
        from frappe.utils import get_system_timezone
        import pytz
        
        # Parse the email date (this returns a timezone-aware datetime)
        dt = parsedate_to_datetime(date_string)
        
        # Convert to system timezone
        system_tz = pytz.timezone(get_system_timezone())
        dt_system = dt.astimezone(system_tz)
        
        return dt_system.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        frappe.log_error(f"Error parsing email date {date_string}: {str(e)}")
        return now_datetime()


def parse_iso_datetime(iso_string):
    """
    Parse ISO 8601 datetime string to Frappe datetime format
    Convert to system timezone
    """
    from datetime import datetime
    from frappe.utils import get_system_timezone
    import pytz
    
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
                # Make it timezone-aware (UTC)
                dt = dt.replace(tzinfo=pytz.UTC)
            else:
                # Without microseconds
                dt = datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S')
                # Make it timezone-aware (UTC)
                dt = dt.replace(tzinfo=pytz.UTC)
        
        # Convert to system timezone
        system_tz = pytz.timezone(get_system_timezone())
        dt_system = dt.astimezone(system_tz)
        
        # Convert to Frappe's expected format
        return dt_system.strftime('%Y-%m-%d %H:%M:%S')
        
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
    Enhanced version with better inline image handling
    """
    inline_images = {}  # Map content_id to file_url for HTML replacement
    has_attachments = False
    
    # Sort attachments to process inline images first, in correct order
    inline_attachments = [att for att in attachments if att.get("is_inline", False)]
    regular_attachments = [att for att in attachments if not att.get("is_inline", False)]
    
    # Process inline images first
    for attachment in inline_attachments:
        try:
            filename = attachment.get("filename")
            content_type = attachment.get("content_type")
            content = attachment.get("content")
            content_id = attachment.get("content_id")
            
            if content and filename:
                # Create File document
                file_doc = create_file_document(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    communication=communication
                )
                
                # Track inline images for HTML content replacement
                if content_id:
                    inline_images[content_id] = file_doc.file_url
                    frappe.log(f"Processed inline image: CID={content_id}, Filename={filename}, URL={file_doc.file_url}")
        
        except Exception as e:
            frappe.log_error(
                message=f"Error processing inline image {filename}: {str(e)}",
                title="Inline Image Processing Error"
            )
    
    # Process regular attachments
    for attachment in regular_attachments:
        try:
            filename = attachment.get("filename")
            content_type = attachment.get("content_type")
            content = attachment.get("content")
            
            if content and filename:
                # Create File document
                file_doc = create_file_document(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    communication=communication
                )
                
                has_attachments = True
                frappe.log(f"Processed regular attachment: {filename}")
        
        except Exception as e:
            frappe.log_error(
                message=f"Error processing attachment {filename}: {str(e)}",
                title="Attachment Processing Error"
            )
    
    # Replace cid: references in HTML content with actual file URLs
    if inline_images and communication.content:
        updated_content = communication.content
        
        # Log the replacement process
        frappe.log(f"Replacing CID references in HTML content. Found {len(inline_images)} inline images.")
        
        for content_id, file_url in inline_images.items():
            # Replace cid:content_id with the actual file URL
            cid_pattern = f"cid:{content_id}"
            if cid_pattern in updated_content:
                updated_content = updated_content.replace(cid_pattern, file_url)
                frappe.log(f"Replaced {cid_pattern} with {file_url}")
            else:
                frappe.log(f"Warning: CID pattern {cid_pattern} not found in HTML content")
        
        communication.content = updated_content
    
    # Update has_attachment flag
    if has_attachments or inline_images:
        if has_attachments:
            communication.has_attachment = 1
        
        # Save communication 
        communication.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.log(f"Updated communication {communication.name} with {len(inline_images)} inline images and {len(regular_attachments)} regular attachments")


def process_attachments(communication, attachments, email_data):
    """
    Process email attachments and save them as File documents
    Legacy function - keeping for backward compatibility
    Also handles inline images and updates HTML content references
    """
    s3_bucket = email_data.get("s3_bucket")
    s3_key = email_data.get("s3_key")
    inline_images = {}  # Map content_id to file_url for HTML replacement
    has_attachments = False
    
    for attachment in attachments:
        try:
            filename = attachment.get("filename")
            content_type = attachment.get("content_type")
            size = attachment.get("size", 0)
            content_id = attachment.get("content_id")
            is_inline = attachment.get("is_inline", False)
            
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
                
                # Track if we have any regular attachments (not inline images)
                if not is_inline:
                    has_attachments = True
                
                # Track inline images for HTML content replacement
                if is_inline and content_id:
                    inline_images[content_id] = file_doc.file_url
        
        except Exception as e:
            frappe.log_error(
                message=f"Error processing attachment {filename}: {str(e)}",
                title="Attachment Processing Error"
            )
    
    # Replace cid: references in HTML content with actual file URLs
    if inline_images and communication.content:
        updated_content = communication.content
        
        for content_id, file_url in inline_images.items():
            # Replace cid:content_id with the actual file URL
            cid_pattern = f"cid:{content_id}"
            updated_content = updated_content.replace(cid_pattern, file_url)
        
        communication.content = updated_content
    
    # Update has_attachment flag
    if has_attachments:
        communication.has_attachment = 1
    
    # Save communication 
    if has_attachments or inline_images:
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
    Create a Support Issue from the Communication record with enhanced reply detection
    """
    try:
        # Get In-Reply-To and find parent communication
        parent_communication = None
        if hasattr(communication, 'in_reply_to') and communication.in_reply_to:
            parent_communication = frappe.get_doc("Communication", communication.in_reply_to)
        
        # Check if an issue already exists using enhanced logic
        existing_issue = find_existing_issue_enhanced(
            communication.subject, 
            sender_email,
            parent_communication=parent_communication
        )
        
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
        
        frappe.log(f"Successfully created support issue {issue.name} from communication {communication.name}")
        
        return issue
        
    except Exception as e:
        frappe.log_error(
            message=f"Error creating support issue from communication {communication.name}: {str(e)}",
            title="Support Issue Creation Error"
        )
        return None


def find_parent_communication(in_reply_to):
    """
    Find parent communication using In-Reply-To header (similar to Frappe's approach)
    """
    try:
        # First try to find by message_id
        communication = frappe.db.get_value(
            "Communication", 
            {"message_id": in_reply_to}, 
            "name",
            order_by="creation desc"
        )
        
        if communication:
            return frappe.get_doc("Communication", communication)
        
        # If message contains @, split and try the part before @
        if "@" in in_reply_to:
            reference, _ = in_reply_to.split("@", 1)
            communication = frappe.db.get_value("Communication", reference, "name")
            if communication:
                return frappe.get_doc("Communication", communication)
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error finding parent communication: {str(e)}")
        return None


def get_thread_id_from_subject(subject):
    """
    Extract thread ID from subject using Frappe's pattern
    """
    try:
        matches = THREAD_ID_PATTERN.findall(subject)
        return matches[0] if matches else None
    except Exception:
        return None


def find_existing_issue_enhanced(subject, sender_email, in_reply_to=None, parent_communication=None):
    """
    Enhanced version of find_existing_issue using Frappe's threading logic
    """
    try:
        # Method 1: If we have a parent communication, get issue from it
        if parent_communication and parent_communication.reference_doctype == "Issue":
            return parent_communication.reference_name
        
        # Method 2: Extract thread ID from subject
        thread_id = get_thread_id_from_subject(subject)
        if thread_id:
            # Try to find issue by name/ID from thread
            if frappe.db.exists("Issue", thread_id):
                return thread_id
        
        # Method 3: Extract issue name from subject (e.g., "Re: Issue ISS-2024-001")
        issue_name = extract_reference_name_from_subject(subject)
        if issue_name and frappe.db.exists("Issue", issue_name):
            return issue_name
        
        # Method 4: Clean subject for matching (remove Re:, Fwd:, etc.)
        clean_subject = clean_subject_for_matching(subject)
        
        # Method 5: Look for existing issues with similar subject from same sender (within 60 days)
        from frappe.utils import add_days
        sixty_days_ago = add_days(get_datetime(), -60)
        
        issues = frappe.get_list(
            "Issue",
            filters={
                "raised_by": sender_email,
                "status": ["not in", ["Closed", "Resolved"]],
                "creation": [">=", sixty_days_ago]
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


def extract_reference_name_from_subject(subject):
    """
    Extract reference name from subject (similar to Frappe's get_reference_name_from_subject)
    Ex: "Re: Issue ISS-2024-001 - Problem" -> "ISS-2024-001"
    """
    try:
        # Look for patterns like ISS-YYYY-NNNN, ISSUE-NNNN, etc.
        patterns = [
            r'(ISS-\d{4}-\d+)',
            r'(ISSUE-\d+)',
            r'(\w+-\d{4}-\d+)',  # General pattern like XXX-YYYY-NNNN
            r'#([A-Z0-9-]+)'     # Hash-prefixed references
        ]
        
        for pattern in patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: extract from end of subject after #
        if '#' in subject:
            return subject.rsplit('#', 1)[-1].strip(' ()')
        
        return None
        
    except Exception:
        return None


def clean_subject_for_matching(subject):
    """
    Clean subject for matching (similar to Frappe's clean_subject)
    """
    # Match strings like "fw:", "re:", etc.
    regex = r"(^\s*(fw|fwd|wg)[^:]*:|\s*(re|aw)[^:]*:\s*)*"
    return re.sub(regex, "", subject, count=0, flags=re.IGNORECASE).strip()


def find_existing_issue(subject, sender_email):
    """
    Legacy method - kept for backward compatibility
    """
    return find_existing_issue_enhanced(subject, sender_email)


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
        
        frappe.log(f"Linked communication {communication.name} to issue {issue_name}")
        
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
    Now supports multiple comma-separated emails in the associated_email field
    """
    try:
        if not to_emails:
            return None
        
        # Get all user groups with associated emails
        user_groups_with_emails = frappe.db.get_list(
            "User Group",
            filters={"custom_associated_email": ["!=", ""]},
            fields=["name", "custom_associated_email"]
        )
        
        # Check each recipient email against user groups with associated emails
        for email in to_emails:
            email = email.strip().lower()
            
            # Check each user group's associated emails
            for user_group in user_groups_with_emails:
                if not user_group.custom_associated_email:
                    continue
                
                # Split the associated emails by comma and check each one
                associated_emails = [e.strip().lower() for e in user_group.custom_associated_email.split(',')]
                
                if email in associated_emails:
                    frappe.log(f"Auto-assigned issue to user group: {user_group.name} based on associated email: {email}")
                    return user_group.name
        
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
    When an incoming customer email is linked to an existing Issue, update response status fields:
    Set "Customer Awaits Reply" to true and "Awaiting Customer Response" to false
    """
    try:
        issue_doc = frappe.get_doc("Issue", issue_name)

        # Update response status fields - customer replied, so they now await our reply
        response_status_changed = False
        
        # Set "Customer Awaits Reply" to true and "Awaiting Customer Response" to false
        if not issue_doc.custom_is_response_expected:
            issue_doc.custom_is_response_expected = 1
            response_status_changed = True
            
        if issue_doc.custom_is_response_awaited:
            issue_doc.custom_is_response_awaited = 0
            response_status_changed = True

        # Save the issue if any changes were made
        if response_status_changed:
            issue_doc.save(ignore_permissions=True)

            # Log a comment on the Issue for traceability
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Issue",
                "reference_name": issue_name,
                "content": _("Response status updated: Customer now awaits reply."),
                "comment_by": "Administrator" if frappe.flags.in_test else frappe.session.user
            }).insert(ignore_permissions=True)

            frappe.log(f"Issue {issue_name} updated after customer reply: Response Expected=True, Response Awaited=False")

    except Exception as e:
        frappe.log_error(
            message=f"Error updating response status for Issue {issue_name}: {str(e)}",
            title="Response Status Update Error"
        )