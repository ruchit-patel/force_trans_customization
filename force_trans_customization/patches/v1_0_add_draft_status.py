import frappe

def execute():
    """Add Draft status to Communication doctype"""
    
    # Get the Communication doctype
    communication_doc = frappe.get_doc("DocType", "Communication")
    
    # Find the status field
    status_field = None
    for field in communication_doc.fields:
        if field.fieldname == "status":
            status_field = field
            break
    
    if status_field:
        # Add "Draft" to the options if it's not already there
        options = status_field.options or ""
        if "Draft" not in options:
            if options:
                status_field.options = options + "\nDraft"
            else:
                status_field.options = "Draft"
            
            # Save the doctype
            communication_doc.save()
            frappe.db.commit()
            
            print("✅ Added 'Draft' status to Communication doctype")
        else:
            print("ℹ️  'Draft' status already exists in Communication doctype")
    else:
        print("❌ Status field not found in Communication doctype") 