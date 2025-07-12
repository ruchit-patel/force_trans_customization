import frappe

def execute():
    """Add 'Draft' to delivery_status options in Communication doctype"""
    communication_doc = frappe.get_doc("DocType", "Communication")
    for field in communication_doc.fields:
        if field.fieldname == "delivery_status":
            options = field.options or ""
            if "Draft" not in options:
                if options:
                    field.options = options + "\nDraft"
                else:
                    field.options = "Draft"
                communication_doc.save()
                frappe.db.commit()
                print("✅ Added 'Draft' to delivery_status options in Communication doctype")
            else:
                print("ℹ️  'Draft' already exists in delivery_status options")
            break
    else:
        print("❌ delivery_status field not found in Communication doctype") 