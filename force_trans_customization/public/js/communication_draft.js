// Enhanced CommunicationComposer with draft functionality
frappe.provide('force_trans_customization.communication_draft');

force_trans_customization.communication_draft = {
    init() {
        this.setup_draft_functionality();
    },

    setup_draft_functionality() {
        // Remove auto-save from content field
        const original_get_fields = frappe.views.CommunicationComposer.prototype.get_fields;
        frappe.views.CommunicationComposer.prototype.get_fields = function () {
            let fields = original_get_fields.call(this);
            // Remove onchange from content field
            fields = fields.map(field => {
                if (field.fieldname === "content" && field.onchange) {
                    delete field.onchange;
                }
                return field;
            });
            return fields;
        };

        // Add Save As Draft button after dialog is created
        const original_make = frappe.views.CommunicationComposer.prototype.make;
        frappe.views.CommunicationComposer.prototype.make = function () {
            original_make.call(this);
            // Add Save As Draft button to dialog footer
            const me = this;
            const $footer = $(this.dialog.$wrapper).find('.modal-footer');
            if ($footer.find('.save-as-draft-btn').length === 0) {
                const $btn = $('<button class="btn btn-default save-as-draft-btn" style="margin-right: 8px;">' + __("Save As Draft") + '</button>');
                $btn.insertBefore($footer.find('.btn-primary, .btn-secondary').first());
                $btn.on('click', function () {
                    me.save_as_draft();
                });
            }
        };

        const original_save_as_draft = frappe.views.CommunicationComposer.prototype.save_as_draft;
        frappe.views.CommunicationComposer.prototype.save_as_draft = function () {
            if (this.dialog && this.frm) {
                let form_values = this.dialog.get_values();
                // Use draft_name if present (editing existing draft)
                let draft_name = this.draft_name || (form_values && form_values.draft_name);

                console.log("Saving draft with draft_name:", draft_name);

                // Call our server-side save method
                frappe.call({
                    method: "force_trans_customization.api.email_draft.save_draft",
                    args: {
                        doctype: this.frm.doctype,
                        docname: this.frm.docname,
                        subject: form_values.subject,
                        recipients: form_values.recipients,
                        content: form_values.content,
                        cc: form_values.cc,
                        bcc: form_values.bcc,
                        sender: form_values.sender,
                        email_template: form_values.email_template,
                        draft_name: draft_name
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft saved"), 3);
                            // Update draft_name for future saves
                            if (r.message.draft_name) {
                                this.draft_name = r.message.draft_name;
                                console.log("Updated draft_name to:", this.draft_name);
                            }
                            // Refresh timeline to show updated draft
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
                            }
                            // Close the email composer dialog
                            if (this.dialog) {
                                this.dialog.hide();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error saving draft"),
                                indicator: "red"
                            });
                        }
                    }.bind(this)
                });

                // Also call the original method for local storage
                original_save_as_draft.call(this);
            }
        };

        // Override send_action to handle draft emails and add 30-second delay
        const original_send_action = frappe.views.CommunicationComposer.prototype.send_action;
        frappe.views.CommunicationComposer.prototype.send_action = async function () {
            // Add 30-second delay to send_after if not specified (for both draft and non-draft)
            let form_values = this.dialog.get_values();
            console.log("=== DEBUG: Communication Draft Send Action ===");
            console.log("Form values:", form_values);

            // Check if send_after is already set by user
            const currentSendAfter = form_values ? form_values.send_after : null;
            console.log("Current send_after value:", currentSendAfter);
            console.log("send_after field exists:", 'send_after' in (form_values || {}));

            let isDelayedSending = false;
            let communicationName = null;

            if (!currentSendAfter) {
                console.log("send_after is empty, applying 30-second delay");
                // Calculate 30 seconds from now in Frappe's configured timezone
                const now = new Date();
                const sendAfter = new Date(now.getTime() + 30 * 1000);

                // Convert to Frappe's timezone and format properly
                const sendAfterInTimezone = frappe.datetime.convert_to_user_tz(sendAfter);
                const formattedDateTime = frappe.datetime.get_datetime_as_string(sendAfterInTimezone);

                console.log("Setting send_after to:", formattedDateTime);

                // Set the send_after value in the dialog
                await this.dialog.set_value('send_after', formattedDateTime);

                // Debug: Check if the value was set
                const afterSetValue = this.dialog.get_value('send_after');
                console.log("After setting send_after, get_value returns:", afterSetValue);

                isDelayedSending = true;
            } else {
                console.log("send_after is already set, not applying delay");
            }

            // Check if this is editing a draft
            if (this.draft_name) {
                // This is editing a draft, so update the existing draft and send it
                let form_values = this.dialog.get_values();
                if (!form_values) return;

                const selected_attachments = $.map(
                    $(this.dialog.wrapper).find("[data-file-name]:checked"),
                    function (element) {
                        return $(element).attr("data-file-name");
                    }
                );

                // Call our server-side send draft method
                frappe.call({
                    method: "force_trans_customization.api.email_draft.send_draft",
                    args: {
                        draft_name: this.draft_name,
                        form_values: form_values,
                        selected_attachments: selected_attachments
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            communicationName = r.message.communication_name;


                            if (isDelayedSending) {
                                // Show toast with undo button for delayed sending
                                this.show_undo_toast(communicationName);
                            } else {
                                frappe.show_alert(__("Draft sent successfully"), 3);
                            }

                            this.dialog.hide();
                            // Refresh timeline
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error sending draft"),
                                indicator: "red"
                            });
                        }
                    }.bind(this)
                });
            } else {
                // This is a new email, use the original send action but intercept the result
                const originalSendAction = original_send_action.bind(this);


                // Override the original send action to capture the communication name
                original_send_action.call(this);

                // If delayed sending is enabled, we need to find the communication that was just created
                if (isDelayedSending) {
                    // Wait a bit for the communication to be created, then find it
                    setTimeout(function () {
                        this.find_recent_communication_and_show_undo();
                    }.bind(this), 1000);
                }
            }
        };

        // Override the get_earlier_reply function to format quoted content properly
        const original_get_earlier_reply = frappe.views.CommunicationComposer.prototype.get_earlier_reply;
        frappe.views.CommunicationComposer.prototype.get_earlier_reply = function () {
            this.reply_set = false;

            const last_email = this.last_email || (this.frm && this.frm.timeline.get_last_email(true));

            if (!last_email) return "";
            let last_email_content = last_email.original_comment || last_email.content;

            // Clean up the HTML content properly
            last_email_content = this.clean_html_content(last_email_content);

            // clip last email for a maximum of 20k characters
            // to prevent the email content from getting too large
            if (last_email_content.length > 20 * 1024) {
                last_email_content += "<div>" + __("Message clipped") + "</div>" + last_email_content;
                last_email_content = last_email_content.slice(0, 20 * 1024);
            }

            const communication_date = frappe.datetime.global_date_format(
                last_email.communication_date || last_email.creation
            );

            this.reply_set = true;

            return `
                <div><br></div>
                <div class="gmail_quote">
                    <div class="gmail_attr">
                        ${__("On {0}, {1} wrote:", [communication_date, last_email.sender])}
                    </div>
                    <blockquote class="gmail_quote" style="margin:0px 0px 0px 0.8ex;border-left:1px solid rgb(204,204,204);padding-left:1ex;">
                        ${last_email_content}
                    </blockquote>
                </div>
            `;
        };

        // New function to clean HTML content
        frappe.views.CommunicationComposer.prototype.clean_html_content = function (html) {
            if (!html) return "";

            // Create a temporary div to parse HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;

            // Remove table elements that cause unwanted formatting
            const tablesToRemove = tempDiv.querySelectorAll('table, tbody, thead, tr, td, th');
            tablesToRemove.forEach(el => {
                // Replace table cells with their text content and line break
                if (el.tagName === 'TD' || el.tagName === 'TH') {
                    const textContent = el.textContent.trim();
                    if (textContent) {
                        el.outerHTML = textContent + '\n';
                    } else {
                        el.remove();
                    }
                } else {
                    // For other table elements, just unwrap them
                    while (el.firstChild) {
                        el.parentNode.insertBefore(el.firstChild, el);
                    }
                    el.remove();
                }
            });

            // Convert block elements to preserve line breaks
            const blockElements = tempDiv.querySelectorAll('div, p, br');
            blockElements.forEach(el => {
                if (el.tagName === 'BR') {
                    el.outerHTML = '\n';
                } else if (el.tagName === 'DIV' || el.tagName === 'P') {
                    // Add line break after block elements
                    const textContent = el.textContent.trim();
                    if (textContent) {
                        el.outerHTML = textContent + '\n';
                    } else {
                        el.remove();
                    }
                }
            });

            // Handle blockquotes specially to preserve structure
            const blockquotes = tempDiv.querySelectorAll('blockquote');
            blockquotes.forEach(blockquote => {
                const textContent = blockquote.textContent.trim();
                if (textContent) {
                    blockquote.outerHTML = textContent + '\n';
                } else {
                    blockquote.remove();
                }
            });

            // Remove other complex elements that can cause formatting issues
            const complexElements = tempDiv.querySelectorAll('iframe, object, embed, style, script');
            complexElements.forEach(el => el.remove());

            // Get the text content and clean it up
            let content = tempDiv.textContent || tempDiv.innerText || "";

            // Clean up excessive whitespace while preserving line breaks
            content = content
                .replace(/[ \t]+/g, ' ')        // Multiple spaces/tabs to single space
                .replace(/\n{3,}/g, '\n\n')     // More than 2 line breaks to 2
                .replace(/^\s+|\s+$/gm, '')     // Remove leading/trailing spaces from lines
                .trim();                        // Remove leading/trailing whitespace

            // Ensure email headers (On [date]...) start on new lines
            // First handle cases where there's text immediately before "On"
            content = content.replace(/([a-zA-Z0-9!.\-\s])On\s+(\d{1,2}(st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December|\w{3})\s+\d{4})/g, '$1\nOn $2');

            // Also handle Gmail-style email headers "On ... at ... wrote:"
            content = content.replace(/([a-zA-Z0-9!.\-\s])On\s+([A-Z][a-z]{2},\s+[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}\s+(AM|PM))/g, '$1\nOn $2');

            // Ensure "Sent via" also starts on new line
            content = content.replace(/([a-zA-Z0-9!.\-\s])(Sent via)/g, '$1\n$2');

            // Remove duplicate "Sent via ERPNext" signatures (keep only the first one)
            const sentViaRegex = /Sent via\s*ERPNext/gi;
            const matches = content.match(sentViaRegex);
            if (matches && matches.length > 1) {
                // Replace all occurrences except the first one
                let count = 0;
                content = content.replace(sentViaRegex, function (match) {
                    count++;
                    return count === 1 ? match : '';
                });
            }

            // Clean up any extra line breaks left by removing signatures
            content = content.replace(/\n{3,}/g, '\n\n');

            // Convert back to HTML with proper line breaks
            content = content.replace(/\n/g, '<br>');

            return content;
        };

        frappe.views.CommunicationComposer.prototype.html2text = function (html) {
            // convert HTML to text and try and preserve whitespace
            html = html
                .replace(/<\/div>/g, "<br></div>") // replace end of blocks
                .replace(/<\/p>/g, "<br></p>") // replace end of paragraphs
                .replace(/<br>/g, "\n");

            const text = frappe.utils.html2text(html);

            // Clean up excessive newlines and spacing
            return text
                .replace(/\n{3,}/g, "\n\n") // Replace 3+ consecutive newlines with 2
                .replace(/ +/g, " ") // Replace multiple spaces with single space
                .replace(/^\s+|\s+$/gm, ""); // Remove leading/trailing whitespace from each line
        };

        // Add method to show undo toast
        frappe.views.CommunicationComposer.prototype.show_undo_toast = function (communicationName) {
            if (!communicationName) return;

            const toast = frappe.show_alert({
                message: __("Email will be sent in 30 seconds. ") +
                    ` <a class="text-small text-muted undo-email-btn" href="#" data-communication="${communicationName}" style="font-weight: bold; text-decoration: underline;">${__("Undo")}</a>`,
                indicator: "yellow"
            }, 30);

            // Add click handler for undo button
            toast.find('.undo-email-btn').on('click', function () {
                const commName = this.draft_name || communicationName;
                frappe.call({
                    method: "force_trans_customization.api.email_draft.undo_scheduled_email",
                    args: {
                        communication_name: commName
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Email sending cancelled"), 3);
                            // Refresh timeline
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error cancelling email"),
                                indicator: "red"
                            });
                        }
                    }.bind(this)
                });

                // Remove the toast
                toast.remove();
            }.bind(this));
        };

        // Add method to find recent communication and show undo
        frappe.views.CommunicationComposer.prototype.find_recent_communication_and_show_undo = function () {
            // Use our custom server-side method to get the most recent communication
            frappe.call({
                method: "force_trans_customization.api.email_draft.get_recent_communication",
                args: {
                    doctype: this.frm.doctype,
                    docname: this.frm.docname,
                    minutes: 1
                },
                callback: function (r) {
                    console.log("Recent communication result:", r.message);
                    if (r.message && r.message.name) {
                        console.log("Using communication:", r.message.name, "created at:", r.message.creation);
                        this.show_undo_toast(r.message.name);
                    } else {
                        console.log("No recent communications found for undo");
                    }
                }.bind(this)
            });
        };


    },

    delete_draft(draft_name) {
        frappe.confirm(
            __("Are you sure you want to delete this draft?"),
            function () {
                frappe.call({
                    method: "force_trans_customization.api.email_draft.delete_draft",
                    args: {
                        draft_name: draft_name
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft deleted"), 3);
                            // Refresh timeline
                            if (cur_frm && cur_frm.timeline) {
                                cur_frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error deleting draft"),
                                indicator: "red"
                            });
                        }
                    }
                });
            }
        );
    }
};

force_trans_customization.communication_draft.open_composer_with_draft = function (draft_doc) {
    // Open the CommunicationComposer dialog with draft_doc's data
    const composer = new frappe.views.CommunicationComposer({
        doc: cur_frm.doc,
        frm: cur_frm,
        subject: draft_doc.subject,
        recipients: draft_doc.recipients,
        message: draft_doc.content, // Use 'message' instead of 'content'
        cc: draft_doc.cc,
        bcc: draft_doc.bcc,
        sender: draft_doc.sender,
        email_template: draft_doc.email_template,
        // Track draft_name for updating
        draft_name: draft_doc.name
    });
    // Attach draft_name to the composer instance for later use
    composer.draft_name = draft_doc.name;
};

// Initialize when page loads
$(function () {
    force_trans_customization.communication_draft.init();
}); 