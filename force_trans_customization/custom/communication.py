import frappe
from frappe import _

def set_email_account_from_user_group(communication_doc):
	"""
	Set email account on communication document based on user's group association
	"""
	try:
		# Get the current user (who is sending the email)
		current_user = communication_doc.sender or frappe.session.user
		
		# Get user group email account data (optimized to return both name and email_id)
		user_group_email_data = get_user_group_email_account_for_user(current_user)
		
		if user_group_email_data:
			email_account_name = user_group_email_data['email_account_name']
			email_id = user_group_email_data['email_id']
			
			# Set the email account on the communication document
			communication_doc.db_set('email_account', email_account_name, update_modified=False)
			
			# Override the sender field with the email account's email
			if email_id:
				communication_doc.db_set('sender', email_id, update_modified=False)
			
			frappe.log(f"Set email account {email_account_name} and sender {email_id} for communication {communication_doc.name}")
		else:
			frappe.log(f"No user group email account found for user {current_user}")
			
	except Exception as e:
		frappe.log_error(
			message=f"Error setting email account from user group: {str(e)}",
			title="Communication Email Account Error"
		)

def get_user_group_email_account_for_user(user_email):
	"""
	Get the email account associated with the user's group
	Returns a dict with email account name and email_id if found, None otherwise
	"""
	try:
		# Get all user groups where the current user is a member and join with email account
		email_account_data = frappe.db.sql("""
			SELECT ea.name as email_account_name, ea.email_id
			FROM `tabUser Group` ug
			INNER JOIN `tabUser Group Member` ugm ON ugm.parent = ug.name
			INNER JOIN `tabEmail Account` ea ON ea.email_id = ug.custom_associated_email
			WHERE ugm.user = %s 
				AND ug.custom_associated_email IS NOT NULL 
				AND ug.custom_associated_email != ''
				AND ea.enable_outgoing = 1
			ORDER BY ug.creation DESC
			LIMIT 1
		""", user_email, as_dict=True)
		
		if email_account_data:
			result = {
				'email_account_name': email_account_data[0].get('email_account_name'),
				'email_id': email_account_data[0].get('email_id')
			}
			frappe.log(f"Found email account {result['email_account_name']} with email {result['email_id']} for user {user_email}")
			return result
		else:
			frappe.log(f"No enabled email account found for user {user_email}")
		
	except Exception as e:
		frappe.log_error(
			message=f"Error getting user group email account: {str(e)}",
			title="User Group Email Account Error"
		)
	
	return None

def on_communication_after_insert(doc, method):
	"""
	Hook to update issue status when a support agent sends an email to customer
	and set appropriate email account based on user group
	"""
	# Set email account based on user group for outgoing emails
	if doc.communication_medium == "Email" and doc.sent_or_received == "Sent":
		set_email_account_from_user_group(doc)
	
	if not doc.reference_doctype == "Issue":
		return
		
	if not doc.reference_name:
		return
		
	# Only process outgoing emails (sent by support agents)
	if doc.sent_or_received != "Sent":
		return
		
	# Only process email communications
	if doc.communication_medium != "Email":
		return
		
	# Check if this is a reply to a customer (not internal communication)
	if not is_customer_email(doc):
		return
		
	# Update issue status based on current state
	update_issue_status_after_agent_reply(doc.reference_name)

def is_customer_email(communication_doc):
	"""
	Check if the email is being sent to a customer/lead
	"""
	# Get the issue document
	try:
		issue_doc = frappe.get_doc("Issue", communication_doc.reference_name)
	except frappe.DoesNotExistError:
		return False
	
	# Get all recipient emails
	recipients = communication_doc.recipients or ""
	cc_emails = communication_doc.cc or ""
	bcc_emails = communication_doc.bcc or ""
	
	all_emails = []
	if recipients:
		all_emails.extend([email.strip() for email in recipients.split(",")])
	if cc_emails:
		all_emails.extend([email.strip() for email in cc_emails.split(",")])
	if bcc_emails:
		all_emails.extend([email.strip() for email in bcc_emails.split(",")])
	
	# Check if any of the emails match the issue's customer email
	customer_emails = []
	
	# Get customer email from issue's raised_by field (most common case)
	if issue_doc.raised_by:
		customer_emails.append(issue_doc.raised_by)
	
	# Check linked lead
	if issue_doc.lead:
		lead_doc = frappe.get_doc("Lead", issue_doc.lead)
		if lead_doc.email_id:
			customer_emails.append(lead_doc.email_id)
	
	# Check linked contact
	if issue_doc.contact:
		contact_doc = frappe.get_doc("Contact", issue_doc.contact)
		# Get primary email from contact
		for email_row in contact_doc.email_ids:
			if email_row.is_primary:
				customer_emails.append(email_row.email_id)
				break
		# If no primary email, get the first one
		if not any(email_row.is_primary for email_row in contact_doc.email_ids) and contact_doc.email_ids:
			customer_emails.append(contact_doc.email_ids[0].email_id)
	
	# Check linked customer
	if issue_doc.customer:
		customer_doc = frappe.get_doc("Customer", issue_doc.customer)
		if customer_doc.customer_primary_contact:
			contact_doc = frappe.get_doc("Contact", customer_doc.customer_primary_contact)
			# Get primary email from customer's primary contact
			for email_row in contact_doc.email_ids:
				if email_row.is_primary:
					customer_emails.append(email_row.email_id)
					break
			# If no primary email, get the first one
			if not any(email_row.is_primary for email_row in contact_doc.email_ids) and contact_doc.email_ids:
				customer_emails.append(contact_doc.email_ids[0].email_id)
	
	# Check if any recipient is a customer email
	for email in all_emails:
		if email in customer_emails:
			return True
	
	# If no direct match, check if it's not an internal email (not from company domain)
	# This is a fallback to catch external emails
	company_domains = get_company_email_domains()
	for email in all_emails:
		email_domain = email.split("@")[-1] if "@" in email else ""
		if email_domain and email_domain not in company_domains:
			return True
	
	return False

def get_company_email_domains():
	"""
	Get list of company email domains to identify internal vs external emails
	"""
	domains = set()
	
	# Get domains from email accounts
	email_accounts = frappe.get_all("Email Account", 
		fields=["email_id"], 
		filters={"enable_outgoing": 1}
	)
	
	for account in email_accounts:
		if account.email_id and "@" in account.email_id:
			domain = account.email_id.split("@")[-1]
			domains.add(domain)
	
	# Get domains from company settings
	# Note: Currently we only use email account domains
	# You can add company-specific domain logic here if needed in the future
	# For example, if companies have specific email domains they use
	
	return list(domains)

def update_issue_status_after_agent_reply(issue_name):
	"""
	Update response status fields after an agent sends an email to the customer.
	Sets "Awaiting Customer Response" to true and "Customer Awaits Reply" to false.
	"""
	try:
		issue_doc = frappe.get_doc("Issue", issue_name)

		# Set the response status fields similar to the JS logic
		issue_doc.custom_is_response_awaited = 1
		issue_doc.custom_is_response_expected = 0
		
		issue_doc.save()

		# Log the change for traceability
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Issue",
			"reference_name": issue_name,
			"content": _("Issue marked as awaiting customer response"),
			"comment_by": frappe.session.user
		}).insert(ignore_permissions=True)

	except Exception as e:
		frappe.log_error(f"Error updating response status for {issue_name}: {str(e)}", "Response Status Update Error") 