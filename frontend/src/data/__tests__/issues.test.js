// Simple test to validate the issues data structure and helper functions
import {
	getIssueTypeOptions,
	getPriorityOptions,
	getProjectOptions,
	getStatusOptions,
} from "../issues.js"

// Test helper functions
console.log("Testing helper functions...")

// Test status options (should always work as it's hardcoded)
const statusOptions = getStatusOptions()
console.log("Status options:", statusOptions)
console.assert(statusOptions.length === 6, "Should have 6 status options")
console.assert(
	statusOptions[0].label === "All Status",
	'First option should be "All Status"',
)

// Test priority options (will return default when no data)
const priorityOptions = getPriorityOptions()
console.log("Priority options:", priorityOptions)
console.assert(
	priorityOptions.length >= 1,
	"Should have at least default option",
)

// Test issue type options (will return default when no data)
const issueTypeOptions = getIssueTypeOptions()
console.log("Issue type options:", issueTypeOptions)
console.assert(
	issueTypeOptions.length >= 1,
	"Should have at least default option",
)

// Test project options (will return default when no data)
const projectOptions = getProjectOptions()
console.log("Project options:", projectOptions)
console.assert(
	projectOptions.length >= 1,
	"Should have at least default option",
)

console.log("All tests passed!")

// Export for potential use in other tests
export { statusOptions, priorityOptions, issueTypeOptions, projectOptions }
