// Universal Tag Color Override for Frappe
// This file overrides the default frappe.get_palette function globally
// across all doctypes and views (list, form, kanban, etc.)

(function() {
    'use strict';
    
    // Store the original get_palette function
    const originalGetPalette = frappe.get_palette;
    
    // Dynamic color map that will be populated from Tag Categories
    let customColorMap = {};
    let isColorMapLoaded = false;
    
    // Load tag categories and build color map
    function loadTagCategoryColors() {
        if (isColorMapLoaded) return;
        
        // Fetch all tags with their categories and build the color map
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Tag',
                fields: ['name', 'custom_tag_category'],
                filters: [['custom_tag_category', '!=', '']],
                limit_page_length: 0
            }
        }).then(result => {
            if (!result.message) return;
            
            const tags = result.message;
            const categoryPromises = [];
            
            // Get unique tag categories
            const uniqueCategories = [...new Set(tags.map(tag => tag.custom_tag_category))];
            
            // Fetch all tag category colors
            uniqueCategories.forEach(categoryName => {
                const promise = frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'Tag Category',
                        fieldname: 'category_color',
                        filters: { name: categoryName }
                    }
                });
                categoryPromises.push(promise);
            });
            
            // Wait for all category colors to be fetched
            Promise.all(categoryPromises).then(categoryResults => {
                // Build the color map
                categoryResults.forEach((categoryResult, index) => {
                    if (categoryResult.message && categoryResult.message.category_color) {
                        const categoryName = uniqueCategories[index];
                        const hexColor = categoryResult.message.category_color;
                        
                        // Find all tags that belong to this category
                        const categoryTags = tags.filter(tag => tag.custom_tag_category === categoryName);
                        
                        // Add each tag to the color map
                        categoryTags.forEach(tag => {
                            const colorVars = createCSSVariablesForColor(tag.name, hexColor);
                            customColorMap[tag.name.toLowerCase()] = colorVars;
                        });
                    }
                });
                
                isColorMapLoaded = true;
                console.log('✅ Tag Category color map loaded:', customColorMap);
            });
        });
    }
    
    // Create CSS custom properties for a tag color and return variable names
    function createCSSVariablesForColor(tagName, hexColor) {
        if (!hexColor) return null;
        
        // Remove # if present
        const hex = hexColor.replace('#', '');
        
        // Convert to RGB
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        
        // Create CSS variable names for this tag
        const sanitizedTagName = tagName.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
        const bgVarName = `--tag-${sanitizedTagName}-bg`;
        const colorVarName = `--tag-${sanitizedTagName}-color`;
        
        // Create background color (lighter version)
        const bgColor = `rgba(${r}, ${g}, ${b}, 0.1)`;
        
        // Create text color (darker version for contrast)
        const textColor = `rgb(${Math.max(r - 50, 0)}, ${Math.max(g - 50, 0)}, ${Math.max(b - 50, 0)})`;
        
        // Add CSS custom properties to the document
        const style = document.documentElement.style;
        style.setProperty(bgVarName, bgColor);
        style.setProperty(colorVarName, textColor);
        
        // Return the CSS variable names (what Frappe expects)
        return [bgVarName, colorVarName];
    }
    
    // Custom tag color logic
    function getCustomTagColor(tag) {
        if (!tag) {
            return originalGetPalette.call(this, tag);
        }
        
        // Convert tag to lowercase for consistent matching
        const tagLower = tag.toLowerCase().trim();
        
        // Check if we have a color from Tag Category
        if (customColorMap[tagLower]) {
            return customColorMap[tagLower];
        }
        
        // If no custom mapping found, fall back to original logic
        return originalGetPalette.call(this, tag);
    }
    
    // Override the global frappe.get_palette function
    frappe.get_palette = function(txt) {
        return getCustomTagColor(txt);
    };
    
    // Load color map when DOM is ready
    $(document).ready(function() {
        // Load tag category colors after a short delay to ensure frappe is fully loaded
        loadTagCategoryColors();
    });
    
    console.log('✅ Custom tag color system loaded with Tag Category support - frappe.get_palette overridden');
})(); 