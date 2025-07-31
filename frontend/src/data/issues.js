import { createResource } from "frappe-ui"

// Main resource for fetching Issue doctype data with child table support
export const issuesResource = createResource({
	url: "force_trans_customization.api.issues.get_issues_with_assignments",
	makeParams(params) {
		// Handle null/undefined params explicitly
		const safeParams = params || {}
		const limit_page_length = safeParams.limit_page_length || 10
		const limit_start = safeParams.limit_start || 0
		const filters = safeParams.filters || {}
		const order_by = safeParams.order_by || "creation desc"

		return {
			limit_page_length,
			limit_start,
			filters,
			order_by,
		}
	},
	onError(error) {
		console.error("Failed to fetch issues:", error)
		// Show user-friendly error message using Frappe UI toast
		if (window.$toast) {
			window.$toast({
				title: "Error",
				text: "Failed to load issues. Please try again.",
				icon: "x",
				iconClasses: "text-red-600",
			})
		}
	},
	auto: true, // Auto-fetch on component mount
})

// Resource for getting total count of issues (for pagination)
export const issuesCountResource = createResource({
	url: "force_trans_customization.api.issues.get_issues_count_with_filters",
	makeParams(params) {
		// Handle null/undefined params explicitly
		const safeParams = params || {}
		const filters = safeParams.filters || {}
		return {
			filters,
		}
	},
	onError(error) {
		console.error("Failed to fetch issues count:", error)
	},
})

// Helper function to reload issues with new parameters
export function reloadIssues(params = {}) {
	const reloadParams = {
		limit_page_length: params.limit_page_length || 10,
		limit_start: params.limit_start || 0,
		filters: params.filters || {},
		order_by: params.order_by || "creation desc",
	}
	return issuesResource.reload(reloadParams)
}

// Helper function to get issues count with filters
export function getIssuesCount(filters = {}) {
	return issuesCountResource.reload({ filters })
}

// Resource for fetching a single issue with assignments
export const singleIssueResource = createResource({
	url: "force_trans_customization.api.issues.get_single_issue_with_assignments",
	makeParams(issueName) {
		return {
			issue_name: issueName
		}
	},
	onError(error) {
		console.error("Failed to fetch single issue:", error)
	},
	auto: false, // Don't auto-fetch, only fetch when called
})

// Helper function to fetch a single issue
export function fetchSingleIssue(issueName) {
	return singleIssueResource.reload(issueName)
}

// Resource for fetching Issue Priority options
export const issuePriorityResource = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		return {
			doctype: "Issue Priority",
			fields: ["name"],
			limit_page_length: 0, // Get all priorities
			order_by: "name asc",
		}
	},
	cache: "IssuePriority", // Cache for 5 minutes
	onError(error) {
		console.error("Failed to fetch issue priorities:", error)
	},
	auto: true,
})

// Resource for fetching Issue Type options
export const issueTypeResource = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		return {
			doctype: "Issue Type",
			fields: ["name"],
			limit_page_length: 0, // Get all issue types
			order_by: "name asc",
		}
	},
	cache: "IssueType", // Cache for 5 minutes
	onError(error) {
		console.error("Failed to fetch issue types:", error)
	},
	auto: true,
})

// Resource for fetching Project options
export const projectResource = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		return {
			doctype: "Project",
			fields: ["name", "project_name", "status"],
			filters: {
				status: ["!=", "Cancelled"], // Only active projects
			},
			limit_page_length: 0, // Get all projects
			order_by: "name asc",
		}
	},
	cache: "Project", // Cache for 5 minutes
	onError(error) {
		console.error("Failed to fetch projects:", error)
	},
	auto: true,
})

// Helper functions to get dropdown options
export function getPriorityOptions() {
	const priorities = issuePriorityResource.data || []
	return [
		{ label: "All Priority", value: "" },
		...priorities.map((p) => ({
			label: p.name,
			value: p.name,
		})),
	]
}

export function getIssueTypeOptions() {
	const types = issueTypeResource.data || []
	return [
		{ label: "All Types", value: "" },
		...types.map((t) => ({
			label: t.name,
			value: t.name,
		})),
	]
}

export function getProjectOptions() {
	const projects = projectResource.data || []
	return [
		{ label: "All Projects", value: "" },
		...projects.map((p) => ({
			label: p.project_name || p.name,
			value: p.name,
		})),
	]
}

// Status options (hardcoded as they are standard)
export function getStatusOptions() {
	return [
		{ label: "All Status", value: "" },
		{ label: "Open", value: "Open" },
		{ label: "Replied", value: "Replied" },
		{ label: "On Hold", value: "On Hold" },
		{ label: "Resolved", value: "Resolved" },
		{ label: "Closed", value: "Closed" },
	]
}

// Resource for fetching tag colors from Tag Categories
export const tagColorsResource = createResource({
	url: "force_trans_customization.api.issues.get_tag_colors",
	cache: "TagColors", // Cache for 10 minutes
	onError(error) {
		console.error("Failed to fetch tag colors:", error)
	},
	auto: true, // Auto-fetch on component mount
})

// Helper function to get tag color
export function getTagColor(tagName) {
	const tagColors = tagColorsResource.data || {}
	return tagColors[tagName] || null
}

// Resource for searching issues (for autocomplete suggestions)
export const issueSearchResource = createResource({
	url: "force_trans_customization.api.issues.issue_search",
	makeParams(params) {
		const safeParams = params || {}
		return {
			search_query: safeParams.search_query || "",
			limit: safeParams.limit || 8,
		}
	},
	onError(error) {
		console.error("Failed to search issues:", error)
	},
	auto: false, // Don't auto-fetch, only fetch when called
})

// Helper function to search issues
export function searchIssues(searchQuery, limit = 8) {
	if (!searchQuery || searchQuery.length < 2) {
		return Promise.resolve(issueSearchResource.data || [])
	}
	return issueSearchResource.reload({ search_query: searchQuery, limit }).then(() => {
		return issueSearchResource.data || []
	})
}

// Resource for filtering issues by suggestion
export const suggestionFilterResource = createResource({
	url: "force_trans_customization.api.issues.filter_issues_by_suggestion",
	makeParams(params) {
		const safeParams = params || {}
		return {
			suggestion_type: safeParams.suggestion_type || "",
			suggestion_value: safeParams.suggestion_value || "",
			limit_page_length: safeParams.limit_page_length || 10,
			limit_start: safeParams.limit_start || 0,
			order_by: safeParams.order_by || "creation desc",
		}
	},
	onError(error) {
		console.error("Failed to filter issues by suggestion:", error)
		if (window.$toast) {
			window.$toast({
				title: "Error",
				text: "Failed to filter issues. Please try again.",
				icon: "x",
				iconClasses: "text-red-600",
			})
		}
	},
	auto: false, // Don't auto-fetch, only fetch when called
})

// Resource for getting count of filtered issues by suggestion
export const suggestionFilterCountResource = createResource({
	url: "force_trans_customization.api.issues.get_filtered_issues_count",
	makeParams(params) {
		const safeParams = params || {}
		return {
			suggestion_type: safeParams.suggestion_type || "",
			suggestion_value: safeParams.suggestion_value || "",
		}
	},
	onError(error) {
		console.error("Failed to get filtered issues count:", error)
	},
	auto: false, // Don't auto-fetch, only fetch when called
})

// Helper function to filter issues by suggestion
export function filterIssuesBySuggestion(suggestionType, suggestionValue, params = {}) {
	const filterParams = {
		suggestion_type: suggestionType,
		suggestion_value: suggestionValue,
		limit_page_length: params.limit_page_length || 10,
		limit_start: params.limit_start || 0,
		order_by: params.order_by || "creation desc",
	}
	return suggestionFilterResource.reload(filterParams)
}

// Helper function to get count of filtered issues by suggestion
export function getFilteredIssuesCountBySuggestion(suggestionType, suggestionValue) {
	return suggestionFilterCountResource.reload({
		suggestion_type: suggestionType,
		suggestion_value: suggestionValue,
	})
}

// Helper function to refresh all filter options
export function refreshFilterOptions() {
	issuePriorityResource.reload()
	issueTypeResource.reload()
	projectResource.reload()
	tagColorsResource.reload()
}
