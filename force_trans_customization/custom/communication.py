import frappe
from frappe import _

def on_communication_after_insert(doc, method):
	"""
	Hook to update issue status when a support agent sends an email to customer
	"""
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
	Handle automatic status transitions when a support agent replies to a customer email.

	1. If the Issue is currently "In Transit Unmanaged" → move it to "In Transit".
	2. Otherwise, if the Issue is **not** already "Waiting on Customer" → move it to "Waiting on Customer".
	"""
	try:
		issue_doc = frappe.get_doc("Issue", issue_name)

		current_status = issue_doc.status
		new_status = None

		if current_status == "In Transit Unmanaged":
			new_status = "In Transit"
		elif current_status == "In Review":
			new_status = "Waiting on Customer"

		# Apply the change only if we determined a new status
		if new_status and new_status != current_status:
			issue_doc.status = new_status
			issue_doc.save()

			# Log the change for traceability
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Issue",
				"reference_name": issue_name,
				"content": _(f"Issue status automatically updated to '{new_status}' as an email was sent to the customer."),
				"comment_by": frappe.session.user
			}).insert(ignore_permissions=True)

	except Exception as e:
		frappe.log_error(f"Error updating issue status for {issue_name}: {str(e)}", "Issue Status Update Error") 