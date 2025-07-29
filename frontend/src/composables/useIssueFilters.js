import { ref, computed, watch } from 'vue'

// Simple debounce function
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

export function useIssueFilters() {
  // Reactive state for search and filters
  const searchQuery = ref('')
  const filters = ref({
    status: '',
    priority: '',
    assignee: '',
    tags: '',
    sortBy: 'creation desc'
  })

  // Debounced search to optimize performance
  const debouncedSearchQuery = ref('')
  
  // Create debounced function for search
  const updateDebouncedSearch = debounce((query) => {
    debouncedSearchQuery.value = query
  }, 300) // 300ms delay

  // Watch search query and update debounced version
  watch(searchQuery, (newQuery) => {
    updateDebouncedSearch(newQuery)
  })

  // Computed property for API filters
  const apiFilters = computed(() => {
    const filterObj = {}

    // Add search filter if query exists
    if (debouncedSearchQuery.value.trim()) {
      // Search in subject and description fields
      filterObj['subject'] = ['like', `%${debouncedSearchQuery.value.trim()}%`]
    }

    // Add status filter
    if (filters.value.status) {
      filterObj['status'] = filters.value.status
    }

    // Add priority filter
    if (filters.value.priority) {
      filterObj['priority'] = filters.value.priority
    }

    // Add assignee filter
    if (filters.value.assignee) {
      filterObj['raised_by'] = filters.value.assignee
    }

    // Add tags filter (issue_type)
    if (filters.value.tags) {
      filterObj['issue_type'] = filters.value.tags
    }

    return filterObj
  })

  // Computed property for sort order
  const sortOrder = computed(() => {
    return filters.value.sortBy || 'creation desc'
  })

  // Function to apply filters to a list of issues (client-side filtering)
  const filterIssues = (issues) => {
    if (!issues || !Array.isArray(issues)) return []

    let filteredIssues = [...issues]

    // Apply search filter
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.toLowerCase().trim()
      filteredIssues = filteredIssues.filter(issue => {
        const subject = (issue.subject || '').toLowerCase()
        const description = (issue.description || '').toLowerCase()
        return subject.includes(query) || description.includes(query)
      })
    }

    // Apply status filter
    if (filters.value.status) {
      filteredIssues = filteredIssues.filter(issue => 
        issue.status === filters.value.status
      )
    }

    // Apply priority filter
    if (filters.value.priority) {
      filteredIssues = filteredIssues.filter(issue => 
        issue.priority === filters.value.priority
      )
    }

    // Apply assignee filter
    if (filters.value.assignee) {
      filteredIssues = filteredIssues.filter(issue => 
        issue.raised_by === filters.value.assignee
      )
    }

    // Apply tags filter (issue_type)
    if (filters.value.tags) {
      filteredIssues = filteredIssues.filter(issue => 
        issue.issue_type === filters.value.tags
      )
    }

    // Apply sorting
    filteredIssues.sort((a, b) => {
      const [field, direction] = filters.value.sortBy.split(' ')
      const aValue = a[field] || ''
      const bValue = b[field] || ''

      let comparison = 0
      
      // Handle different field types
      if (field === 'creation' || field === 'modified') {
        comparison = new Date(aValue) - new Date(bValue)
      } else if (field === 'priority') {
        // Custom priority sorting: Critical > High > Medium > Low
        const priorityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 }
        comparison = (priorityOrder[aValue] || 0) - (priorityOrder[bValue] || 0)
      } else {
        // String comparison
        comparison = aValue.toString().localeCompare(bValue.toString())
      }

      return direction === 'desc' ? -comparison : comparison
    })

    return filteredIssues
  }

  // Function to get unique assignees from issues list
  const getAssigneeOptions = (issues) => {
    if (!issues || !Array.isArray(issues)) return [{ label: 'All Assignees', value: '' }]
    
    const uniqueAssignees = [...new Set(
      issues
        .map(issue => issue.raised_by)
        .filter(assignee => assignee && assignee.trim())
    )]

    return [
      { label: 'All Assignees', value: '' },
      ...uniqueAssignees.map(assignee => ({
        label: assignee,
        value: assignee
      }))
    ]
  }

  // Function to reset all filters
  const resetFilters = () => {
    searchQuery.value = ''
    debouncedSearchQuery.value = ''
    filters.value = {
      status: '',
      priority: '',
      assignee: '',
      tags: '',
      sortBy: 'creation desc'
    }
  }

  // Function to check if any filters are active
  const hasActiveFilters = computed(() => {
    return searchQuery.value.trim() !== '' ||
           filters.value.status !== '' ||
           filters.value.priority !== '' ||
           filters.value.assignee !== '' ||
           filters.value.tags !== '' ||
           filters.value.sortBy !== 'creation desc'
  })

  return {
    // Reactive state
    searchQuery,
    filters,
    debouncedSearchQuery,
    
    // Computed properties
    apiFilters,
    sortOrder,
    hasActiveFilters,
    
    // Functions
    filterIssues,
    getAssigneeOptions,
    resetFilters
  }
}