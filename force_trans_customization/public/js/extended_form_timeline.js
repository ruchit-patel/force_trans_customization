// Extended FormTimeline to add draft edit/delete functionality
frappe.provide('force_trans_customization.extended_timeline');

force_trans_customization.extended_timeline = {
    init() {
        this.setup_draft_event_handlers();
        this.setup_form_timeline_hooks();
    },

    setup_form_timeline_hooks() {
        // Hook into the form render process to add draft functionality
        const original_make_timeline = frappe.ui.form.Footer.prototype.make_timeline;
        
        frappe.ui.form.Footer.prototype.make_timeline = function() {
            // Call original make_timeline
            original_make_timeline.call(this);
            
            // Now extend the timeline instance with draft functionality
            if (this.frm.timeline) {
                force_trans_customization.extended_timeline.extend_timeline_instance(this.frm.timeline);
            }
        };
    },

    extend_timeline_instance(timeline) {
        // Store original setup_reply method
        const original_setup_reply = timeline.setup_reply;
        
        // Override setup_reply to add draft buttons
        timeline.setup_reply = function(communication_box, communication_doc) {
            // Call original setup_reply first
            if (original_setup_reply) {
                original_setup_reply.call(this, communication_box, communication_doc);
            }
            
            // Add draft buttons if this is a draft communication
            if (communication_doc && communication_doc._doc_status === 'Draft') {
                force_trans_customization.extended_timeline.setup_draft_buttons(communication_box);
            }
        };
        
        //Store original refresh method to hook into timeline refreshes
        const original_refresh = timeline.refresh;
        timeline.refresh = function() {
            // Call original refresh
            original_refresh.call(this);
        };
    },

    setup_draft_buttons(communication_box) {
        let actions = communication_box.find(".custom-actions");
        
        if (actions.length === 0) {
            console.log('No custom-actions found for draft communication');
            return;
        }
        
        // Check if buttons already exist
        if (actions.find('.edit-draft, .delete-draft').length > 0) {
            return;
        }
        
        // Create edit draft button
        let edit_draft_btn = $(`<a class="action-btn edit-draft" title="${__('Edit Draft')}">${frappe.utils.icon("edit", "md")}</a>`);
        
        // Create delete draft button  
        let delete_draft_btn = $(`<a class="action-btn delete-draft" title="${__('Delete Draft')}">${frappe.utils.icon("delete", "md")}</a>`);
        
        // Add buttons to actions (prepend so they appear first)
        actions.prepend(delete_draft_btn);
        actions.prepend(edit_draft_btn);
    },
    
    setup_draft_event_handlers() {
        // Use event delegation similar to crm_activities.js pattern
        $(document).on('click', '.edit-draft', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const $timeline_item = $(this).closest('.timeline-item');
            const communication_name = $timeline_item.data('name') || $timeline_item.find('[data-name]').first().data('name');
            
            if (!communication_name) {
                console.error('Could not find communication name for draft edit');
                frappe.msgprint(__('Could not identify draft to edit'));
                return;
            }
            
            // Get the draft communication and open composer
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Communication",
                    name: communication_name
                },
                callback: function(r) {
                    if (r.message) {
                        force_trans_customization.extended_timeline.edit_draft_communication(r.message);
                    } else {
                        frappe.msgprint(__('Could not load draft data'));
                    }
                }
            });
        });
        
        $(document).on('click', '.delete-draft', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const $timeline_item = $(this).closest('.timeline-item');
            const communication_name = $timeline_item.data('name') || $timeline_item.find('[data-name]').first().data('name');
            
            if (!communication_name) {
                console.error('Could not find communication name for draft delete');
                frappe.msgprint(__('Could not identify draft to delete'));
                return;
            }
            
            force_trans_customization.extended_timeline.delete_draft_communication(communication_name);
        });
    },
    
    // add_draft_buttons_to_existing_timeline() {
    //     // Find all timeline items that are drafts but don't have buttons yet
    //     $('.timeline-item').each(function() {
    //         const $item = $(this);
    //         const $content = $item.find('.timeline-content, .timeline-message-box');
            
    //         // Skip if buttons already exist
    //         if ($item.find('.edit-draft, .delete-draft').length > 0) {
    //             return;
    //         }
            
    //         // Check if this is a draft by looking for draft indicators
    //         const itemText = $item.text().toLowerCase();
    //         const hasStatusDraft = itemText.includes('status: draft') || itemText.includes('draft');
            
    //         if (hasStatusDraft && $content.length > 0) {
    //             let $actions = $item.find('.custom-actions');
                
    //             if ($actions.length === 0) {
    //                 // Create actions container if it doesn't exist
    //                 $actions = $('<div class="custom-actions" style="margin-top: 8px;"></div>');
    //                 $content.append($actions);
    //             }
                
    //             // Add buttons
    //             const edit_btn = $(`<a class="action-btn edit-draft" title="${__('Edit Draft')}">${frappe.utils.icon("edit", "md")}</a>`);
    //             const delete_btn = $(`<a class="action-btn delete-draft" title="${__('Delete Draft')}">${frappe.utils.icon("delete", "md")}</a>`);
                
    //             $actions.prepend(delete_btn);
    //             $actions.prepend(edit_btn);
    //         }
    //     });
    // },
    
    edit_draft_communication(draft_doc) {
        // Use the existing communication_draft functionality
        if (force_trans_customization && force_trans_customization.communication_draft && 
            force_trans_customization.communication_draft.open_composer_with_draft) {
            force_trans_customization.communication_draft.open_composer_with_draft(draft_doc);
        } else {
            console.error('communication_draft module not available');
            frappe.msgprint(__('Draft editing functionality not available'));
        }
    },
    
    delete_draft_communication(draft_name) {
        // Use the existing communication_draft functionality
        if (force_trans_customization && force_trans_customization.communication_draft && 
            force_trans_customization.communication_draft.delete_draft) {
            force_trans_customization.communication_draft.delete_draft(draft_name);
        } else {
            console.error('communication_draft module not available');
            frappe.msgprint(__('Draft deletion functionality not available'));
        }
    }
};

// Initialize when the DOM is ready
$(document).ready(function() {
        force_trans_customization.extended_timeline.init();
});