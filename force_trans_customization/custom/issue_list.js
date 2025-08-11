// Custom Issue List View with Enhanced Status Colors
// Based on Sales Invoice pattern: https://github.com/frappe/erpnext/blob/develop/erpnext/accounts/doctype/sales_invoice/sales_invoice_list.js

frappe.listview_settings["Issue"] = {
	colwidths: { subject: 6 },
	add_fields: ["priority", "customer"],
	filters: [["status", "=", "New"]],
	
	onload: function (listview) {
		var method = "erpnext.support.doctype.issue.issue.set_multiple_status";

		// Quick Action Buttons for Status Changes
		listview.page.add_action_item(__("Set as New"), function () {
			listview.call_for_selected_items(method, { status: "New" });
		});

		listview.page.add_action_item(__("Set as In Review"), function () {
			listview.call_for_selected_items(method, { status: "In Review" });
		});

		listview.page.add_action_item(__("Set as Confirmed"), function () {
			listview.call_for_selected_items(method, { status: "Confirmed" });
		});

		listview.page.add_action_item(__("Set as In Transit"), function () {
			listview.call_for_selected_items(method, { status: "In Transit" });
		});

		listview.page.add_action_item(__("Set as Delivered"), function () {
			listview.call_for_selected_items(method, { status: "Delivered" });
		});

		listview.page.add_action_item(__("Set as Closed"), function () {
			listview.call_for_selected_items(method, { status: "Closed" });
		});
	},
	
	get_indicator: function (doc) {
		// Comprehensive Status Color Mapping
		// Following ERPNext Sales Invoice pattern with enhanced colors for our workflow
		const status_colors = {
			// Primary Workflow States
			"New": "blue",                      // 🔵 New issues - blue for fresh/attention needed
			"In Review": "orange",              // 🟠 Under review - orange for active progress  
			"Confirmed": "purple",              // 🟣 Confirmed and validated - purple for approval
			"In Transit": "light-blue",         // 🔷 Active transit - light blue for movement
			"Delivered": "green",               // 🟢 Successfully delivered - green for success
			"Closed": "darkgreen",              // 🟢 Fully completed - dark green for finalization
			
			// Legacy Status Support (backward compatibility)
			"Open": "red",                      // 🔴 Legacy open state
			"Replied": "orange",                // 🟠 Legacy replied state  
			"On Hold": "yellow",                // 🟡 Legacy hold state
			"Resolved": "green"                 // 🟢 Legacy resolved state
		};
		
		// Return status indicator: [label, color, filter]
		return [__(doc.status), status_colors[doc.status] || "gray", "status,=," + doc.status];
	},
	
	// Custom right column display
	right_column: "priority"
}; 