import json
import boto3
import urllib3
import logging
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3_client = boto3.client('s3')
http = urllib3.PoolManager()

#ruchit section
# Configuration - Update these values
FRAPPE_BASE_URL = "https://4482e326219d.ngrok-free.app"  # Update with your Frappe URL
FRAPPE_WEBHOOK_ENDPOINT = "/api/method/force_trans_customization.api.email_webhook.save_email"  # Update endpoint
FRAPPE_API_KEY = "2ae35805831d36f"  # Optional: for authentication
FRAPPE_API_SECRET = "64fa007d42b0177"  # Optional: for authentication

#jay section
# FRAPPE_BASE_URL = "https://aac0b20112b1.ngrok-free.app"  # Update with your Frappe URL
# FRAPPE_WEBHOOK_ENDPOINT = "/api/method/force_trans_customization.api.email_webhook.test"  # Update endpoint
# FRAPPE_API_KEY = "2a926329922822d"  # Optional: for authentication
# FRAPPE_API_SECRET = "716ce2a7ff0fdd1"  # Optional: for authentication



def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        # Process each SES record
        for record in event['Records']:
            if 'ses' in record:
                process_ses_email(record['ses'])
            else:
                logger.warning(f"Non-SES record received: {record}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Email processed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def organize_s3_file(bucket, original_key, status, error_type=None):
    """
    Organize S3 file into proper folder structure
    
    Args:
        bucket: S3 bucket name
        original_key: Current S3 key
        status: 'incoming', 'processed', 'failed'
        error_type: 'parse-error', 'api-error', 'validation-error', etc. (only for failed)
    
    Returns:
        new_key: New organized S3 key
    """
    try:
        # Get current UTC date
        now = datetime.utcnow()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        
        # Extract filename from original key
        filename = original_key.split('/')[-1]
        
        # Build new key based on status
        if status == 'failed' and error_type:
            new_key = f'emails/{year}/{month}/{day}/failed/{error_type}/{filename}'
        else:
            new_key = f'emails/{year}/{month}/{day}/{status}/{filename}'
        
        # Skip if the file is already in the target location
        if original_key == new_key:
            logger.info(f"File already in target location: {original_key}")
            return original_key
        
        # Check if we're moving within organized structure
        if original_key.startswith('emails/') and new_key.startswith('emails/'):
            logger.info(f"Moving within organized structure: {original_key} -> {new_key}")
        elif original_key.startswith('emails/'):
            logger.info(f"File already in organized structure, moving to: {new_key}")
        else:
            logger.info(f"Organizing new file: {original_key} -> {new_key}")
        
        # Copy to new location
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': original_key},
            Key=new_key
        )
        
        # Delete original file
        s3_client.delete_object(Bucket=bucket, Key=original_key)
        
        logger.info(f"Successfully organized file to: {new_key}")
        return new_key
        
    except Exception as e:
        logger.error(f"Error organizing S3 file: {str(e)}")
        return original_key  # Return original key if organization fails
        
def process_ses_email(ses_data):
    """Process SES email data and send webhook to Frappe"""
    
    mail_data = ses_data['mail']
    receipt_data = ses_data['receipt']
    
    # Extract basic email information
    message_id = mail_data['messageId']
    timestamp = mail_data['timestamp']
    source = mail_data['source']
    destination = mail_data['destination']
    
    logger.info(f"Processing email - ID: {message_id}, From: {source}, To: {destination}")
    
    # Get S3 object key (email location) - STATIC BUCKET APPROACH
    s3_bucket = "mysesemailbucket"  # Static bucket name
    
    logger.info(f"Searching for email with message ID: {message_id} in bucket: {s3_bucket}")
    
    # SES stores emails at bucket root with message ID as key
    # Try the most common pattern first, then fallback to others
    possible_keys = [
        f"{message_id}",  # Most common: directly at root
        f"emails/{message_id}",
        f"incoming/{message_id}"
    ]
    
    # Try to find the actual file in S3
    original_s3_key = find_email_in_s3(s3_bucket, possible_keys, message_id)
    
    if not original_s3_key:
        logger.error(f"Could not find email file in S3 bucket '{s3_bucket}' with message ID '{message_id}'")
        return
    
    logger.info(f"Found email at S3 location - Bucket: {s3_bucket}, Key: {original_s3_key}")
    
    # Move to incoming folder first
    s3_key = organize_s3_file(s3_bucket, original_s3_key, 'incoming')
    
    # Read email from S3
    email_content = read_email_from_s3(s3_bucket, s3_key)
    if not email_content:
        logger.error("Could not read email from S3")
        # Move to failed/parse-error folder
        organize_s3_file(s3_bucket, s3_key, 'failed', 'parse-error')
        return
    
    # Parse email
    try:
        parsed_email = parse_email(email_content)
        if not parsed_email:
            raise ValueError("Email parsing returned invalid data")
        # Allow empty subjects - just log a warning
        if not parsed_email.get('subject'):
            logger.warning("Email has empty subject - will use default subject")
            parsed_email['subject'] = ''  # Ensure it's an empty string, not None
    except Exception as e:
        logger.error(f"Email parsing failed: {str(e)}")
        # Move to failed/parse-error folder
        organize_s3_file(s3_bucket, s3_key, 'failed', 'parse-error')
        return
    
    # Prepare webhook payload
    webhook_payload = {
        'message_id': message_id,
        'timestamp': timestamp,
        'from_email': source,
        'to_emails': destination,
        'subject': parsed_email.get('subject', ''),
        'body_text': parsed_email.get('body_text', ''),
        'body_html': parsed_email.get('body_html', ''),
        'attachments': parsed_email.get('attachments', []),
        's3_bucket': s3_bucket,
        's3_key': s3_key,
        'headers': parsed_email.get('headers', {})
    }
    
    # Send webhook to Frappe
    webhook_success = send_webhook_to_frappe(webhook_payload)
    
    # Organize based on webhook result
    if webhook_success:
        # Move to processed folder
        final_key = organize_s3_file(s3_bucket, s3_key, 'processed')
        logger.info(f"Email successfully processed and moved to: {final_key}")
    else:
        # Move to failed/api-error folder
        final_key = organize_s3_file(s3_bucket, s3_key, 'failed', 'api-error')
        logger.error(f"Email processing failed, moved to: {final_key}")

def find_email_in_s3(bucket, possible_keys, message_id):
    """Try to find the email file in S3 using various possible key patterns"""
    try:
        for key in possible_keys:
            try:
                # Check if object exists
                s3_client.head_object(Bucket=bucket, Key=key)
                logger.info(f"Found email file at: s3://{bucket}/{key}")
                return key
            except s3_client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                logger.warning(f"Error checking key '{key}': {str(e)}")
                continue
        
        # If none of the standard patterns work, try listing objects with message_id prefix
        logger.info(f"Standard patterns failed. Searching bucket for files containing: {message_id}")
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                MaxKeys=100
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if message_id in key:
                        logger.info(f"Found email file by search: s3://{bucket}/{key}")
                        return key
        except Exception as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding email in S3: {str(e)}")
        return None

def read_email_from_s3(bucket, key):
    """Read email content from S3"""
    try:
        logger.info(f"Reading email from S3 - Bucket: {bucket}, Key: {key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        email_content = response['Body'].read()
        logger.info(f"Successfully read email content ({len(email_content)} bytes)")
        return email_content
    except Exception as e:
        logger.error(f"Error reading email from S3: {str(e)}")
        return None

def parse_email(email_content):
    """Parse email content and extract components with proper ordering"""
    try:
        # Parse the email
        msg = email.message_from_bytes(email_content)
        
        parsed_data = {
            'subject': msg.get('Subject', ''),
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'date': msg.get('Date', ''),
            'body_text': '',
            'body_html': '',
            'attachments': [],
            'headers': dict(msg.items())
        }
        
        # Extract body and attachments with proper ordering
        if msg.is_multipart():
            # First pass: extract HTML content to analyze CID order
            html_content = ""
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if content_type == "text/html" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True)
                    if body:
                        html_content = body.decode('utf-8', errors='ignore')
                        parsed_data['body_html'] = html_content
                        break
            
            # Extract CID order from HTML content
            cid_order = []
            if html_content:
                import re
                cid_pattern = r'src="cid:([^"]+)"'
                for match in re.finditer(cid_pattern, html_content):
                    cid_id = match.group(1)
                    if cid_id not in cid_order:
                        cid_order.append(cid_id)
            
            # Second pass: extract content and collect attachments
            all_attachments = []
            
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Extract body text
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True)
                    if body:
                        parsed_data['body_text'] = body.decode('utf-8', errors='ignore')
                
                # Extract attachments and inline images
                elif "attachment" in content_disposition or "inline" in content_disposition or part.get('Content-ID'):
                    filename = part.get_filename()
                    content_id = part.get('Content-ID')
                    
                    if filename or content_id:
                        attachment_data = part.get_payload(decode=True)
                        if attachment_data:
                            attachment_info = {
                                'filename': filename or f"inline_{content_id.strip('<>')}",
                                'content_type': content_type,
                                'size': len(attachment_data),
                                'content': base64.b64encode(attachment_data).decode('utf-8')
                            }
                            
                            # Add Content-ID for inline images
                            if content_id:
                                clean_cid = content_id.strip('<>')
                                attachment_info['content_id'] = clean_cid
                                attachment_info['is_inline'] = True
                                # Add order index based on HTML appearance
                                if clean_cid in cid_order:
                                    attachment_info['html_order'] = cid_order.index(clean_cid)
                                else:
                                    attachment_info['html_order'] = 999  # Unknown order
                            else:
                                attachment_info['is_inline'] = False
                                attachment_info['html_order'] = 999  # Regular attachments
                                
                            all_attachments.append(attachment_info)
            
            # Sort attachments by HTML appearance order for inline images, then by original order
            inline_images = [att for att in all_attachments if att.get('is_inline', False)]
            regular_attachments = [att for att in all_attachments if not att.get('is_inline', False)]
            
            # Sort inline images by their HTML order
            inline_images.sort(key=lambda x: x.get('html_order', 999))
            
            # Combine: inline images first (in HTML order), then regular attachments
            parsed_data['attachments'] = inline_images + regular_attachments
            
        else:
            # Non-multipart message
            body = msg.get_payload(decode=True)
            if body:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    parsed_data['body_html'] = body.decode('utf-8', errors='ignore')
                else:
                    parsed_data['body_text'] = body.decode('utf-8', errors='ignore')
        
        logger.info(f"Successfully parsed email - Subject: {parsed_data['subject']}, Attachments: {len(parsed_data['attachments'])}")
        
        # Log attachment order for debugging
        for i, att in enumerate(parsed_data['attachments']):
            if att.get('is_inline'):
                logger.info(f"Inline image {i+1}: CID={att.get('content_id')}, HTML_order={att.get('html_order')}, Filename={att.get('filename')}")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing email: {str(e)}")
        raise e  # Re-raise to trigger failed/parse-error handling
    
    
def send_webhook_to_frappe(payload):
    """
    Send webhook to Frappe application
    
    Returns:
        bool: True if successful, False if failed
    """
    try:
        webhook_url = f"{FRAPPE_BASE_URL}{FRAPPE_WEBHOOK_ENDPOINT}"
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add authentication if configured
        if FRAPPE_API_KEY and FRAPPE_API_SECRET:
            headers['Authorization'] = f'token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}'
        
        # Send POST request
        logger.info(f"Sending webhook to: {webhook_url}")
        logger.info(f"Payload size: {len(json.dumps(payload))} characters")
        
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(payload).encode('utf-8'),
            headers=headers,
            timeout=30.0
        )
        
        logger.info(f"Webhook response - Status: {response.status}, Data: {response.data.decode()}")
        
        if response.status == 200:
            logger.info("Webhook sent successfully")
            return True
        else:
            logger.warning(f"Webhook returned non-200 status: {response.status}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending webhook to Frappe: {str(e)}")
        return False