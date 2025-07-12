// Enhanced timeline functionality to show drafts
frappe.provide('force_trans_customization.enhanced_timeline');

force_trans_customization.enhanced_timeline = {
    init() {
        this.enhance_timeline();
    },

    enhance_timeline() {
        // Override the original timeline refresh method
        const original_refresh = frappe.form.FormTimeline.prototype.refresh;
        
        frappe.form.FormTimeline.prototype.refresh = function() {
            // Call original refresh
            original_refresh.call(this);
            
            // Add drafts to timeline
            this.add_drafts_to_timeline();
        };

        // Add method to include drafts in timeline
        frappe.form.FormTimeline.prototype.add_drafts_to_timeline = function() {
            if (!this.frm || !this.frm.doctype || !this.frm.docname) return;

            frappe.call({
                method: "force_trans_customization.api.email_draft.get_drafts",
                args: {
                    doctype: this.frm.doctype,
                    docname: this.frm.docname
                },
                callback: (r) => {
                    if (r.message && r.message.length > 0) {
                        r.message.forEach(draft => {
                            this.add_draft_item(draft);
                        });
                    }
                }
            });
        };

        // Add method to add draft item to timeline
        frappe.form.FormTimeline.prototype.add_draft_item = function(draft_data) {
            const timeline_wrapper = this.wrapper.find('.timeline-wrapper');
            if (!timeline_wrapper.length) return;

            const draft_item = force_trans_customization.communication_draft.add_draft_to_timeline(draft_data);
            
            // Insert at the top of timeline (most recent first)
            timeline_wrapper.prepend(draft_item);
        };
    }
};

// Initialize when page loads
$(function() {
    force_trans_customization.enhanced_timeline.init();
}); 

// Patch timeline instance after render_complete to show 'Draft' badge
$(function() {
    $(document).on('render_complete', function() {
        if (window.cur_frm && cur_frm.timeline && !cur_frm.timeline._patched_for_draft_badge) {
            const original_set_communication_doc_status = cur_frm.timeline.set_communication_doc_status;
            cur_frm.timeline.set_communication_doc_status = function(doc) {
                original_set_communication_doc_status.call(this, doc);
                if (doc.delivery_status === "Draft") {
                    doc._doc_status = "Draft";
                    doc._doc_status_indicator = "yellow";
                }
            };
            cur_frm.timeline._patched_for_draft_badge = true;
        }
    });
}); 