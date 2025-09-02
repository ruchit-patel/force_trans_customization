// Draft icons for Activity timeline - All Doctypes
frappe.provide('force_trans_customization.draft_activity_icons');

// Add edit and delete icons for draft items in timeline
function add_draft_icons_proper() {
    // Find all timeline items
    $('.timeline-item').each(function() {
        const $item = $(this);
        
        // Skip if icons already added
        if ($item.find('.btn-edit-draft, .btn-delete-draft').length > 0) return;
        
        // Look for "Draft" text in the timeline item
        const itemText = $item.text().toLowerCase();
        if (itemText.includes('draft')) {
            
            // Find the actions container or suitable place for icons
            let $actionsContainer = $item.find('.actions, .timeline-item-actions').first();
            
            // If no actions container found, create one
            if ($actionsContainer.length === 0) {
                // Try to find timeline header or suitable parent
                let $target = $item.find('.timeline-item-head, .timeline-item-header').first();
                if ($target.length === 0) {
                    $target = $item.find('.frappe-timestamp, .text-muted').first();
                }
                if ($target.length === 0) {
                    $target = $item.find('.col-8, .col-9, .col-10').first();
                }
                
                if ($target.length > 0) {
                    // Create actions container
                    $actionsContainer = $('<div class="actions" style="display: inline-block; margin-left: 10px;"></div>');
                    $target.append($actionsContainer);
                }
            }
            
            // Create edit draft button using your format
            let edit_draft_btn = $(`
                <a class="action-btn btn-edit-draft" title="${__("Edit Draft")}" style="margin-right: 5px;">
                    ${frappe.utils.icon("edit", "sm")}
                </a>
            `);

            // Create delete draft button using your format
            let delete_draft_btn = $(`
                <a class="action-btn btn-delete-draft" title="${__("Delete Draft")}">
                    ${frappe.utils.icon("delete", "sm")}
                </a>
            `);
            
            // Get draft name from timeline item data attribute
            const draft_name = $item.data('name') || $item.find('[data-name]').first().data('name');
            
            // Add click handlers
            edit_draft_btn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                if (draft_name) {
                    // Call server to get draft details and open composer
                    frappe.call({
                        method: "frappe.client.get",
                        args: {
                            doctype: "Communication",
                            name: draft_name
                        },
                        callback: function(r) {
                            if (r.message) {
                                // Use the existing function from communication_draft.js
                                force_trans_customization.communication_draft.open_composer_with_draft(r.message);
                            }
                        }
                    });
                } else {
                    frappe.msgprint(__("Draft name not found"));
                }
            });
            
            delete_draft_btn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                if (draft_name) {
                    // Use the existing delete function from communication_draft.js
                    force_trans_customization.communication_draft.delete_draft(draft_name);
                } else {
                    frappe.msgprint(__("Draft name not found"));
                }
            });
            
            if ($actionsContainer.length > 0) {
                $actionsContainer.prepend(delete_draft_btn);
                $actionsContainer.prepend(edit_draft_btn);
            } else {
                // Fallback: create actions area and add buttons
                const actionsHtml = `<div class="message-actions" style="margin-top: 8px;"></div>`;
                $item.find('.timeline-message-box, .timeline-content').first().append(actionsHtml);
                $actionsContainer = $item.find('.message-actions');
                $actionsContainer.append(edit_draft_btn);
                $actionsContainer.append(delete_draft_btn);
            }
        }
    });
}

// Run the function when page loads
$(document).ready(function() {
    setTimeout(add_draft_icons_proper, 500);
    
    // Also run when timeline refreshes
    setInterval(add_draft_icons_proper, 2000);
});

// Run when form loads
$(document).on('form-load', function() {
    setTimeout(add_draft_icons_proper, 1000);
});

// Also run on page route change
$(document).on('page-change', function() {
    setTimeout(add_draft_icons_proper, 1000);
});