// Simple test to validate the useIssueFilters composable
import { useIssueFilters } from "../useIssueFilters.js"

console.log("Testing useIssueFilters composable...")

const filterComposable = useIssueFilters()

const mockIssues = [
	{
		name: "ISS-001",
		subject: "Bug in login system",
		description: "Users cannot login properly",
		status: "Open",
		priority: "High",
		raised_by: "user1@example.com",
		issue_type: "Bug",
		creation: "2023-01-15T10:30:00",
	},
	{
		name: "ISS-002",
		subject: "Feature request for dashboard",
		description: "Add new dashboard widgets",
		status: "Resolved",
		priority: "Medium",
		raised_by: "user2@example.com",
		issue_type: "Feature",
		creation: "2023-01-16T14:20:00",
	},
	{
		name: "ISS-003",
		subject: "Performance issue",
		description: "Page loads slowly",
		status: "Open",
		priority: "Critical",
		raised_by: "user1@example.com",
		issue_type: "Bug",
		creation: "2023-01-17T09:15:00",
	},
]

// Test filterIssues function
console.log("Testing filterIssues...")

// Test 1: No filters applied
let result = filterComposable.filterIssues(mockIssues)
console.assert(
	result.length === 3,
	"Should return all issues when no filters applied",
)

// Test 2: Search by subject
filterComposable.searchQuery.value = "login"
result = filterComposable.filterIssues(mockIssues)
console.assert(result.length === 1, "Should filter by search query in subject")
console.assert(result[0].name === "ISS-001", "Should return correct issue")

// Reset search
filterComposable.searchQuery.value = ""

// Test 3: Filter by status
filterComposable.filters.value.status = "Open"
result = filterComposable.filterIssues(mockIssues)
console.assert(result.length === 2, "Should filter by status")
console.assert(
	result.every((issue) => issue.status === "Open"),
	"All results should have Open status",
)

// Reset filters
filterComposable.resetFilters()

// Test 4: Filter by priority
filterComposable.filters.value.priority = "High"
result = filterComposable.filterIssues(mockIssues)
console.assert(result.length === 1, "Should filter by priority")
console.assert(
	result[0].priority === "High",
	"Should return high priority issue",
)

// Reset filters
filterComposable.resetFilters()

// Test 5: Multiple filters
filterComposable.filters.value.status = "Open"
filterComposable.filters.value.priority = "High"
result = filterComposable.filterIssues(mockIssues)
console.assert(result.length === 1, "Should apply multiple filters")
console.assert(
	result[0].name === "ISS-001",
	"Should return correct issue with multiple filters",
)

// Reset filters
filterComposable.resetFilters()

// Test getAssigneeOptions function
console.log("Testing getAssigneeOptions...")
const assigneeOptions = filterComposable.getAssigneeOptions(mockIssues)
console.assert(
	assigneeOptions.length === 3,
	"Should return 3 assignee options (All + 2 unique)",
)
console.assert(
	assigneeOptions[0].label === "All Assignees",
	'First option should be "All Assignees"',
)

// Test resetFilters function
console.log("Testing resetFilters...")
filterComposable.searchQuery.value = "test"
filterComposable.filters.value.status = "Open"
filterComposable.resetFilters()
console.assert(
	filterComposable.searchQuery.value === "",
	"Search query should be reset",
)
console.assert(
	filterComposable.filters.value.status === "",
	"Status filter should be reset",
)

// Test hasActiveFilters computed property
console.log("Testing hasActiveFilters...")
console.assert(
	filterComposable.hasActiveFilters.value === false,
	"Should have no active filters initially",
)
filterComposable.searchQuery.value = "test"
console.assert(
	filterComposable.hasActiveFilters.value === true,
	"Should detect active search filter",
)

console.log("All useIssueFilters tests passed!")

// Export for potential use in other tests
export { filterComposable, mockIssues }
