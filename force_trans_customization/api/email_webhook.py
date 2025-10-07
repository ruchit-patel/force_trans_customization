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
from frappe.utils import now_datetime, strip_html_tags, cstr, get_datetime, today, nowtime, get_string_between, cint
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
        # Use handle_bad_emails to save the problematic email for investigation
        try:
            email_json = json.loads(email_data) if email_data else {}
            raw_email = email_json.get("raw_email", email_data)

            # Try to determine email account from the data
            to_emails = email_json.get("to_emails", [])
            email_account_name = None
            if to_emails:
                email_account_name = find_matching_email_account(to_emails[0], to_emails)

            handle_bad_emails(
                email_account_name=email_account_name,
                uid=email_json.get("message_id", "webhook_unknown"),
                raw=raw_email,
                reason=f"Webhook processing failed: {str(e)}"
            )
        except Exception as handle_error:
            frappe.log_error(f"Failed to handle bad email: {str(handle_error)}")

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
        # NOTE: Don't use message_id from API data as it might be incorrect
        # message_id = email_data.get("message_id")  # This is often wrong!
        timestamp = email_data.get("timestamp")
        from_email = email_data.get("from_email")
        to_emails = email_data.get("to_emails", [])
        subject = decode_email_header(email_data.get("subject", ""))
        body_text = email_data.get("body_text", "")
        body_html = email_data.get("body_html", "")
        attachments = email_data.get("attachments", [])
        headers = email_data.get("headers", {})
        
        # Clean up body text (remove escape characters)
        body_text = body_text.replace("\\r\\n", "\n").replace("\\n", "\n")
        

        if not to_emails or len(to_emails) == 0:
            delivered_to = extract_delivered_to_from_headers(headers)
            if delivered_to:
                to_emails = [delivered_to]
                frappe.log(f"Using Delivered-To header {delivered_to} as to_emails was empty")

        primary_recipient = to_emails[0] if to_emails else ""
        
        # Find matching Email Account
        email_account = find_matching_email_account(primary_recipient, to_emails)
        
        # Extract proper Message-ID from email headers (not from API data!)
        message_id = extract_proper_message_id(headers)
        
        # Extract In-Reply-To header for reply detection
        in_reply_to = headers.get('In-Reply-To', '') or headers.get('in-reply-to', '')
        if in_reply_to:
            in_reply_to = get_string_between('<', in_reply_to, '>')
        
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
        # Use handle_bad_emails to save the problematic email for investigation
        try:
            raw_email = email_data.get("raw_email", json.dumps(email_data))
            to_emails = email_data.get("to_emails", [])
            email_account_name = None
            if to_emails:
                email_account_name = find_matching_email_account(to_emails[0], to_emails)

            handle_bad_emails(
                email_account_name=email_account_name,
                uid=email_data.get("message_id", "ses_email_unknown"),
                raw=raw_email,
                reason=f"SES email processing failed: {str(e)}"
            )
        except Exception as handle_error:
            frappe.log_error(f"Failed to handle bad SES email: {str(handle_error)}")

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
        
        # Handle empty to_emails with Delivered-To fallback
        if not to_emails or len(to_emails) == 0:
            delivered_to = extract_delivered_to_from_headers(dict(msg.items()))
            if delivered_to:
                to_emails = [delivered_to]
                frappe.log(f"Using Delivered-To header {delivered_to} as to_emails was empty in raw email processing")
        
        # Find matching Email Account
        primary_recipient = to_emails[0] if to_emails else ""
        email_account = find_matching_email_account(primary_recipient, to_emails)
        
        # Extract In-Reply-To header for reply detection
        in_reply_to = msg.get('In-Reply-To', '')
        if in_reply_to:
            in_reply_to = get_string_between('<', in_reply_to, '>')
        
        # Extract message_id properly using our enhanced function
        if message_id:
            # Use the same function for consistency
            message_id = extract_proper_message_id({'Message-ID': message_id})
        else:
            # Try to extract from all headers
            message_id = extract_proper_message_id(dict(msg.items()))
        
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
        # Use handle_bad_emails to save the problematic email for investigation
        try:
            # Try to parse email to get minimal info for saving
            msg = email.message_from_string(raw_email_content) if raw_email_content else None
            to_emails = []
            email_account_name = None

            if msg:
                to_header = msg.get('To', '')
                if to_header:
                    to_emails = [addr.strip() for addr in to_header.split(',')]
                    email_account_name = find_matching_email_account(to_emails[0], to_emails) if to_emails else None

            handle_bad_emails(
                email_account_name=email_account_name,
                uid=msg.get('Message-ID', 'raw_email_unknown') if msg else 'raw_email_unknown',
                raw=raw_email_content,
                reason=f"Raw email processing failed: {str(e)}"
            )
        except Exception as handle_error:
            frappe.log_error(f"Failed to handle bad raw email: {str(handle_error)}")

        frappe.log_error(
            message=f"Error in process_raw_email: {str(e)}",
            title="Raw Email Processing Error"
        )
        raise


def extract_proper_message_id(headers):
    """
    Extract the proper Message-ID from email headers.
    This looks for the actual Message-ID header that looks like:
    Message-ID: <CACCeexFCJQ5BEoeu_+79T+c6AzFg3waURQMjr-OHUFLra_iQNA@mail.gmail.com>
    """
    try:
        # Try different case variations of Message-ID header
        message_id_variations = [
            'Message-ID',
            'message-id', 
            'MESSAGE-ID',
            'Message-Id'
        ]
        
        message_id = ""
        for header_name in message_id_variations:
            if header_name in headers:
                message_id = headers[header_name]
                break
        
        if not message_id:
            frappe.log("Warning: No Message-ID header found in email")
            return ""
        
        # Clean the message ID - remove < > brackets if present
        cleaned_id = get_string_between('<', message_id, '>')
        if not cleaned_id:
            # If no brackets found, use the full string but clean it
            cleaned_id = message_id.strip()
        
        frappe.log(f"DEBUG: Raw Message-ID header: {message_id}")
        frappe.log(f"DEBUG: Extracted Message-ID: {cleaned_id}")
        
        # Validate that the Message-ID looks reasonable
        if cleaned_id and '@' in cleaned_id:
            frappe.log(f"SUCCESS: Valid Message-ID extracted: {cleaned_id}")
        elif cleaned_id:
            frappe.log(f"WARNING: Message-ID doesn't contain '@': {cleaned_id}")
        
        return cleaned_id
        
    except Exception as e:
        frappe.log_error(f"Error extracting Message-ID from headers: {str(e)}")
        return ""

def decode_email_header(header_value):
    """
    Decode email header that might be encoded (RFC 2047 MIME encoded-word format)
    Handles formats like =?UTF-8?B?...?= and =?UTF-8?Q?...?=
    """
    if not header_value:
        return ""
    
    try:
        # Handle multiple encoded-word segments that may be split across lines
        # Remove any line breaks and spaces between encoded words
        import re
        
        # Remove line breaks and normalize spaces between encoded words
        header_value = re.sub(r'\s*\n\s*', ' ', str(header_value))
        header_value = re.sub(r'(\?=)\s+(=\?)', r'\1\2', header_value)
        
        # Use Python's email.header.decode_header function
        decoded_header = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                # Try the specified encoding first, then fallback to utf-8
                try:
                    if encoding:
                        decoded_string += part.decode(encoding, errors='replace')
                    else:
                        decoded_string += part.decode('utf-8', errors='replace')
                except (UnicodeDecodeError, LookupError):
                    # If encoding fails, try utf-8 as fallback
                    decoded_string += part.decode('utf-8', errors='replace')
            else:
                decoded_string += str(part)
        
        # Clean up any remaining artifacts
        decoded_string = decoded_string.strip()
        
        frappe.log(f"Decoded email header: '{header_value}' -> '{decoded_string}'")
        return decoded_string
        
    except Exception as e:
        frappe.log_error(f"Error decoding email header '{header_value}': {str(e)}")
        # Fallback: return the original string if decoding fails
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


def clean_html_content_for_issue(html_content):
    """
    Thoroughly clean HTML content for issue description by removing all HTML tags, CSS, and scripts
    """
    if not html_content:
        return ""
    
    import re
    
    # Remove CSS style blocks (including content between <style> tags)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove script blocks
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove CSS media queries and other CSS declarations that might be outside style tags
    html_content = re.sub(r'@media[^{]*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', html_content, flags=re.DOTALL)
    
    # Remove CSS rules that look like "property: value;" patterns
    html_content = re.sub(r'[a-zA-Z-]+\s*:\s*[^;]+;', '', html_content)
    
    # Remove remaining CSS blocks with curly braces
    html_content = re.sub(r'\{[^}]*\}', '', html_content)
    
    # Use Frappe's built-in function to strip HTML tags
    clean_text = strip_html_tags(html_content)
    
    # Additional cleanup for any remaining CSS-like patterns
    clean_text = re.sub(r'[a-zA-Z-]+\s*:\s*[^;]+;', '', clean_text)
    
    # Remove excessive whitespace and newlines
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', clean_text)
    
    # Clean up common email artifacts
    clean_text = re.sub(r'^\s*["\']?\s*', '', clean_text)  # Remove leading quotes and whitespace
    clean_text = re.sub(r'\s*["\']?\s*$', '', clean_text)  # Remove trailing quotes and whitespace
    
    return clean_text.strip()


def create_communication_record(message_id, timestamp, from_email, to_emails,
                              subject, body_text, body_html, headers, email_account, in_reply_to=None):
    """
    Create a Communication record similar to how Frappe handles IMAP/POP emails
    """
    communication = None
    try:
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

    except Exception as e:
        # Use handle_bad_emails to save the problematic email for investigation
        try:
            # Create raw email content from available data
            raw_email_data = {
                "message_id": message_id,
                "from_email": from_email,
                "to_emails": to_emails,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
                "headers": headers,
                "timestamp": timestamp
            }

            handle_bad_emails(
                email_account_name=email_account,
                uid=message_id or "communication_unknown",
                raw=json.dumps(raw_email_data, default=str),
                reason=f"Communication creation failed: {str(e)}"
            )
        except Exception as handle_error:
            frappe.log_error(f"Failed to handle bad communication email: {str(handle_error)}")

        frappe.log_error(
            message=f"Error creating communication record: {str(e)}",
            title="Communication Creation Error"
        )
        raise


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
        file_doc.is_private = 1
        
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


def handle_bad_emails(email_account_name, uid, raw, reason):
    """
    Save the email in Unhandled Email doctype when processing fails.
    Similar to EmailAccount.handle_bad_emails() but adapted for webhook processing.

    Args:
        email_account_name: Name of the email account
        uid: Unique identifier for the email (can be webhook ID or message ID)
        raw: Raw email content (string or bytes)
        reason: Reason for failure
    """
    try:
        import email as email_lib

        # Handle both string and bytes input
        if isinstance(raw, bytes):
            raw_str = raw.decode("ASCII", "replace")
            try:
                mail = email_lib.message_from_string(raw_str)
                message_id = mail.get("Message-ID", "")
            except Exception:
                message_id = "can't be parsed"
        else:
            try:
                raw_str = str(raw).encode(errors="replace").decode()
                mail = email_lib.message_from_string(raw_str)
                message_id = mail.get("Message-ID", "")
            except Exception:
                raw_str = str(raw) if raw else "can't be parsed"
                message_id = "can't be parsed"

        # Create Unhandled Email document
        unhandled_email = frappe.get_doc({
            "doctype": "Unhandled Email",
            "raw": raw_str,
            "uid": str(uid) if uid else "",
            "reason": str(reason),
            "message_id": message_id,
            "email_account": email_account_name or ""
        })

        unhandled_email.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(
            message=f"Email saved to Unhandled Email: {reason}\nUID: {uid}\nMessage-ID: {message_id}",
            title="Webhook Email Processing Failed"
        )

        return unhandled_email.name

    except Exception as e:
        frappe.log_error(
            message=f"Error saving bad email to Unhandled Email: {str(e)}\nOriginal reason: {reason}",
            title="Handle Bad Email Error"
        )
        return None





import re, html

def clean_email_for_issue(raw: str) -> str:
    """
    Strip CSS/HTML and return readable email text.
    - Removes <style>...</style>
    - Removes <div>, <span>, <em> and their inner content
    - Removes all HTML tags
    - Drops CSS-like lines (selectors, properties, @media)
    - Unescapes HTML entities
    - Normalizes blank lines
    """
    if not raw:
        return ""

    text = raw

    # 1) Remove <style>...</style> blocks
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # 2) Remove "junk wrapper" tags completely including their inner text
    # (div, span, em)
    text = re.sub(r"<(?:div|span|em)[^>]*>.*?</(?:div|span|em)>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # 3) Remove any remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # 4) Split into lines and drop CSS-like lines
    lines = text.splitlines()
    css_prop_re = re.compile(r"^\s*[a-zA-Z-]+\s*:\s*[^;]+;\s*$")   # e.g., color: #000;
    selector_re = re.compile(r"[{}]")                              # contains { or }
    media_re = re.compile(r"^\s*@media\b", re.IGNORECASE)

    kept = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            kept.append("")
            continue

        if media_re.search(line_stripped) or selector_re.search(line_stripped) or css_prop_re.match(line_stripped):
            continue

        # Drop leftover selector-like lines (.class .subclass ...)
        if re.match(r"^\.[\w\-\s.,]+$", line_stripped):
            continue

        kept.append(line)

    text = "\n".join(kept)

    # 5) Unescape HTML entities
    text = html.unescape(text)

    # 6) Trim whitespace
    text = "\n".join(l.strip() for l in text.splitlines())

    # 7) Collapse 3+ blank lines -> 2, and multiple spaces -> single
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


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
        
        # if not sender_email and subject :
        #     frappe.log("No sender email found, cannot create support issue.")
        #     return None

        print("Creating new support issue...")
        print("-------------------------------------------")
        print(f"Subject: {communication.subject}")
        print(f"From: {sender_email}")

        if sender_email is None and  communication.subject == "Delivery Status Notification (Failure)":
            frappe.log_error(
            message=f"No sender email found for delivery failure notification in communication {communication.name}",
            title="Support Issue Creation Skipped"
            )
            return None
        
        # Create a new Issue
        issue = frappe.new_doc("Issue")
        
        # Set basic fields - truncate subject to 140 characters to avoid database errors
        subject = communication.subject or "Support Request"
        issue.subject = subject[:140] if len(subject) > 140 else subject
        issue.raised_by = sender_email
        # Use clean text content for issue description, strip HTML if needed
        if communication.text_content:
            issue.description = clean_email_for_issue(communication.text_content)
        elif communication.content:
            # Strip HTML tags and CSS from content to get clean text
            issue.description = clean_email_for_issue(communication.content)
        else:
            issue.description = ""
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
        user_group = get_user_group_by_recipient_email(to_emails, communication.email_account, headers=getattr(communication, 'email_headers', None))
        if user_group:
            issue.custom_assigned_csm_team = user_group
        else:
            # If no user group found, try to get any as fallback
            default_group = get_default_user_group()
            if default_group:
                issue.custom_assigned_csm_team = default_group
            else:
                frappe.log_error(
                    message=f"No user group could be assigned for email to: {to_emails}. Email Account: {communication.email_account}",
                    title="User Group Assignment Warning"
                )
        
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


def extract_delivered_to_from_headers(headers):
    """
    Extract the Delivered-To header from email headers as fallback when to_emails is empty
    """
    try:
        # Try different case variations of Delivered-To header
        delivered_to_variations = [
            'Delivered-To',
            'delivered-to', 
            'DELIVERED-TO',
            'Delivered-to'
        ]
        
        delivered_to = ""
        for header_name in delivered_to_variations:
            if header_name in headers:
                delivered_to = headers[header_name]
                break
        
        if not delivered_to:
            # Also try X-Original-To as another fallback
            x_original_to_variations = [
                'X-Original-To',
                'x-original-to',
                'X-ORIGINAL-TO'
            ]
            
            for header_name in x_original_to_variations:
                if header_name in headers:
                    delivered_to = headers[header_name]
                    break
        
        if delivered_to:
            # Clean the email address - remove < > brackets if present
            delivered_to = delivered_to.strip()
            if '<' in delivered_to and '>' in delivered_to:
                # Extract email from "Name <email@domain.com>" format
                start = delivered_to.find('<')
                end = delivered_to.find('>')
                if start != -1 and end != -1:
                    delivered_to = delivered_to[start+1:end]
            
            frappe.log(f"DEBUG: Extracted Delivered-To: {delivered_to}")
            return delivered_to.strip()
        
        frappe.log("WARNING: No Delivered-To or X-Original-To header found")
        return None
        
    except Exception as e:
        frappe.log_error(f"Error extracting Delivered-To from headers: {str(e)}")
        return None


def get_user_group_by_recipient_email(to_emails, email_account=None, headers=None):
    """
    Map recipient email addresses to user groups for auto-assignment
    Uses the custom_associated_email field from User Group doctype
    Now supports multiple comma-separated emails in the associated_email field

    Enhanced to handle:
    - Forwarded emails (extracts X-Forwarded-To, X-Original-To)
    - Bounce addresses (extracts Return-Path, X-Failed-Recipients)
    - Fallback to email account's default user group
    """
    try:
        if not to_emails:
            return None

        # Parse headers if provided as JSON string
        parsed_headers = {}
        if headers:
            if isinstance(headers, str):
                try:
                    parsed_headers = json.loads(headers)
                except:
                    pass
            elif isinstance(headers, dict):
                parsed_headers = headers

        # Get all user groups with associated emails
        user_groups_with_emails = frappe.db.get_list(
            "User Group",
            filters={"custom_associated_email": ["!=", ""]},
            fields=["name", "custom_associated_email"]
        )

        # Collect all possible recipient emails to check
        emails_to_check = []

        # 1. Add direct recipients
        for email in to_emails:
            emails_to_check.append(email.strip().lower())

        # 2. Extract original recipients from forwarded email headers
        if parsed_headers:
            forward_headers = ['X-Forwarded-To', 'X-Original-To', 'X-Forwarded-For']
            for header in forward_headers:
                if header in parsed_headers:
                    forwarded_email = parsed_headers[header].strip()
                    if '<' in forwarded_email and '>' in forwarded_email:
                        forwarded_email = forwarded_email[forwarded_email.find('<')+1:forwarded_email.find('>')]
                    emails_to_check.append(forwarded_email.lower())
                    frappe.log(f"Found forwarded recipient: {forwarded_email} from header {header}")

            # 3. Check for bounce/failure scenarios - extract original recipient
            bounce_headers = ['X-Failed-Recipients', 'X-Actual-Recipients', 'Final-Recipient']
            for header in bounce_headers:
                if header in parsed_headers:
                    failed_email = parsed_headers[header].strip()
                    # Parse formats like "rfc822; user@domain.com"
                    if ';' in failed_email:
                        failed_email = failed_email.split(';')[-1].strip()
                    if '<' in failed_email and '>' in failed_email:
                        failed_email = failed_email[failed_email.find('<')+1:failed_email.find('>')]
                    emails_to_check.append(failed_email.lower())
                    frappe.log(f"Found failed recipient: {failed_email} from header {header}")

        # Check each collected email against user groups
        for email in emails_to_check:
            # Check each user group's associated emails
            for user_group in user_groups_with_emails:
                if not user_group.custom_associated_email:
                    continue

                # Split the associated emails by comma and check each one
                associated_emails = [e.strip().lower() for e in user_group.custom_associated_email.split(',')]

                if email in associated_emails:
                    frappe.log(f"Auto-assigned issue to user group: {user_group.name} based on email: {email}")
                    return user_group.name

        return None

    except Exception as e:
        frappe.log_error(f"Error mapping email to user group: {str(e)}")
        return None


def get_default_user_group():
    """
    Get default user group for unmatched emails
    based on First available user group as last resort
    """
    try:
        # Last resort: get the first available user group
        first_group = frappe.db.get_value("User Group", {}, "name")
        if first_group:
            frappe.log(f"Using first available user group as fallback: {first_group}")
            return first_group
        
        return None

    except Exception as e:
        frappe.log_error(f"Error getting default user group: {str(e)}")
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