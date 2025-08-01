<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div class="flex items-center space-x-4">
            <h1 class="text-2xl font-bold text-gray-900">Issue Tracker</h1>
            <nav class="flex space-x-4">
              <router-link to="/" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                Home
              </router-link>
              <router-link to="/issue-tracker"
                class="bg-blue-100 text-blue-700 px-3 py-2 rounded-md text-sm font-medium">
                Issues
              </router-link>
            </nav>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">{{ session.user }}</span>
            <Button @click="session.logout.submit()" theme="gray" variant="outline" size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Statistics Cards -->
      <IssueStats :issues="issues" />

      <!-- Search and Filters -->
      <IssueFilters v-model:searchQuery="searchQuery" v-model:filters="filters" :statusOptions="statusOptions"
        :priorityOptions="priorityOptions" :assigneeOptions="assigneeOptions" :tagsOptions="tagsOptions"
        :issues="allIssues" :filteredCount="totalIssues" @suggestion-selected="handleSuggestionSelected" />

      <!-- Issues Table -->
      <IssueTable :issues="issues" :loading="isLoading" :sortField="currentSortField"
        :sortDirection="currentSortDirection" @sort="handleSort" />

      <!-- Pagination -->
      <IssuePagination v-model:currentPage="currentPage" v-model:itemsPerPage="itemsPerPage" :totalItems="totalIssues"
        @pageChange="handlePageChange" />

      <!-- Compact Real-time Status Icons (Vertical) -->
      <div class="fixed top-20 right-4 flex flex-col space-y-2">
        <!-- Connection Status -->
        <div
          class="group relative bg-white rounded-full shadow-lg border p-2 hover:shadow-xl transition-all duration-200"
          :title="realtimeEventsSetup ? 'Real-time updates active' : 'Real-time updates disabled'">
          <!-- Connection Icon with Status -->
          <div class="relative">
            <FeatherIcon :name="realtimeEventsSetup ? 'wifi' : 'wifi-off'" :class="[
              'h-5 w-5 transition-colors duration-200',
              realtimeEventsSetup ? 'text-green-600' : 'text-red-500'
            ]" />
            <!-- Status Dot -->
            <div :class="[
              'absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white',
              realtimeEventsSetup
                ? 'bg-green-500 animate-pulse'
                : 'bg-red-500'
            ]"></div>
            <!-- Pending Updates Badge -->
            <div v-if="pendingDocumentRefreshes > 0"
              class="absolute -top-2 -right-2 bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium animate-bounce">
              {{ pendingDocumentRefreshes > 9 ? '9+' : pendingDocumentRefreshes }}
            </div>
          </div>
        </div>

        <!-- Manual Refresh Button -->
        <button @click="manualRefresh"
          class="group bg-white rounded-full shadow-lg border p-2 hover:shadow-xl hover:bg-blue-50 transition-all duration-200 active:scale-95"
          title="Manual refresh">
          <FeatherIcon name="refresh-cw"
            class="h-5 w-5 text-gray-600 group-hover:text-blue-600 group-active:rotate-180 transition-all duration-300" />
        </button>
      </div>
    </div>

    <!-- Real-time Notifications -->
    <RealTimeNotifications :notifications="notifications" @remove="removeNotification" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import { Button, FeatherIcon } from "frappe-ui"
import IssueFilters from "../components/IssueFilters.vue"
import IssuePagination from "../components/IssuePagination.vue"
import IssueStats from "../components/IssueStats.vue"
import IssueTable from "../components/IssueTable.vue"
import RealTimeNotifications from "../components/RealTimeNotifications.vue"
import { useIssueFilters } from "../composables/useIssueFilters"
import { useIssueListUpdates } from "../composables/useIssueListUpdates"
import {
  getIssueTypeOptions,
  getIssuesCount,
  getPriorityOptions,
  getStatusOptions,
  issuesCountResource,
  issuesResource,
  reloadIssues,
  filterIssuesBySuggestion,
  getFilteredIssuesCountBySuggestion,
  suggestionFilterResource,
  suggestionFilterCountResource,
} from "../data/issues"
import { session } from "../data/session"

// Use the filtering composable
const {
  searchQuery,
  filters,
  debouncedSearchQuery,
  apiFilters,
  sortOrder,
  getAssigneeOptions,
} = useIssueFilters()

// State to track if we're using suggestion-based filtering
const isUsingSuggestionFilter = ref(false)
const currentSuggestion = ref(null)

// Realtime list updates composable (Frappe-style)
const {
  pendingDocumentRefreshes,
  realtimeEventsSetup,
  manualRefresh
} = useIssueListUpdates(() => {
  // Return current parameters for realtime updates (excluding search filters)
  return {
    filters: nonSearchFilters.value,
    order_by: sortOrder.value,
    limit_page_length: itemsPerPage.value,
    limit_start: (currentPage.value - 1) * itemsPerPage.value,
  }
})

// Simplified notification system for list updates
const notifications = ref([])

const addNotification = (notification) => {
  notifications.value.push({
    id: Date.now() + Math.random(),
    ...notification
  })

  // Auto-remove after 5 seconds
  setTimeout(() => {
    removeNotification(notifications.value[notifications.value.length - 1]?.id)
  }, 5000)
}

const removeNotification = (id) => {
  notifications.value = notifications.value.filter(n => n.id !== id)
}

// Computed properties for displaying data
const allIssues = computed(() => {
  // Use suggestion filter data if active, otherwise use regular issues data
  if (isUsingSuggestionFilter.value) {
    return suggestionFilterResource.data || []
  }
  return issuesResource.data || []
})

const totalIssues = computed(() => {
  // Use suggestion filter count if active, otherwise use regular count
  if (isUsingSuggestionFilter.value) {
    return suggestionFilterCountResource.data || 0
  }
  return issuesCountResource.data || 0
})

const isLoading = computed(() => {
  // Check loading state of active resource
  if (isUsingSuggestionFilter.value) {
    return suggestionFilterResource.loading
  }
  return issuesResource.loading
})

// With server-side pagination, we use the data directly without client-side filtering
const issues = computed(() => allIssues.value)

// Sort functionality
const currentSortField = computed(() => {
  const order = sortOrder.value || "creation desc"
  return order.split(" ")[0]
})

const currentSortDirection = computed(() => {
  const order = sortOrder.value || "creation desc"
  return order.split(" ")[1] || "desc"
})

const handleSort = ({ field, direction }) => {
  // Update the sort order in the composable
  const newSortOrder = `${field} ${direction}`
  // This will trigger the watcher and reload data
  filters.value.sortBy = newSortOrder
}

// Handle suggestion selection from search
const handleSuggestionSelected = (suggestion) => {
  // Switch to suggestion-based filtering mode
  isUsingSuggestionFilter.value = true
  currentSuggestion.value = suggestion

  // Set search query to show the selected suggestion in the search box
  searchQuery.value = suggestion.subject || suggestion.name

  // Reset to first page when suggestion is selected
  currentPage.value = 1

  // Determine suggestion type based on what was clicked
  // For now, we'll use "name" as the default type for exact match
  const suggestionType = "name"
  const suggestionValue = suggestion.name

  // Filter issues using the new suggestion-based API
  filterIssuesBySuggestion(suggestionType, suggestionValue, {
    limit_page_length: itemsPerPage.value,
    limit_start: 0,
    order_by: sortOrder.value,
  })

  // Get count for pagination
  getFilteredIssuesCountBySuggestion(suggestionType, suggestionValue)
}

// Function to clear suggestion filter and return to normal search
const clearSuggestionFilter = () => {
  isUsingSuggestionFilter.value = false
  currentSuggestion.value = null
  searchQuery.value = ""
  
  // Reset to first page
  currentPage.value = 1
  
  // Reload with normal filters (excluding search)
  reloadIssues({
    filters: nonSearchFilters.value,
    order_by: sortOrder.value,
    limit_page_length: itemsPerPage.value,
    limit_start: 0,
  })
  
  // Reload count
  getIssuesCount(nonSearchFilters.value)
}

// Filter options
const priorityOptions = computed(() => getPriorityOptions())
const tagsOptions = computed(() => getIssueTypeOptions()) // Issue types as tags
const statusOptions = computed(() => getStatusOptions())
const assigneeOptions = computed(() => getAssigneeOptions(allIssues.value))

// Pagination state
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Pagination handler
const handlePageChange = ({ page, itemsPerPage: newItemsPerPage, offset }) => {
  currentPage.value = page
  itemsPerPage.value = newItemsPerPage

  if (isUsingSuggestionFilter.value && currentSuggestion.value) {
    // Use suggestion-based filtering for pagination
    const suggestionType = "name"
    const suggestionValue = currentSuggestion.value.name

    filterIssuesBySuggestion(suggestionType, suggestionValue, {
      limit_page_length: newItemsPerPage,
      limit_start: offset,
      order_by: sortOrder.value,
    })
  } else {
    // Use regular filtering for pagination (excluding search)
    reloadIssues({
      filters: nonSearchFilters.value,
      order_by: sortOrder.value,
      limit_page_length: newItemsPerPage,
      limit_start: offset,
    })

    // Also reload count with current filters
    getIssuesCount(nonSearchFilters.value)
  }
}

// Create computed property for non-search filters only
const nonSearchFilters = computed(() => {
  const filterObj = {}

  // Add status filter
  if (filters.value.status) {
    filterObj["status"] = filters.value.status
  }

  // Add priority filter
  if (filters.value.priority) {
    filterObj["priority"] = filters.value.priority
  }

  // Add assignee filter
  if (filters.value.assignee) {
    filterObj["raised_by"] = filters.value.assignee
  }

  // Add tags filter (issue_type)
  if (filters.value.tags) {
    filterObj["issue_type"] = filters.value.tags
  }

  return filterObj
})

// Watch for filter changes and reload data from server when needed
// Note: We exclude search-related filters to prevent table updates while typing
watch(
  [nonSearchFilters, sortOrder],
  () => {
    // If user is changing filters (not search), exit suggestion mode
    if (isUsingSuggestionFilter.value) {
      isUsingSuggestionFilter.value = false
      currentSuggestion.value = null
    }

    // Reset to first page when filters change
    currentPage.value = 1

    // Reload issues with new filters and sort order
    reloadIssues({
      filters: nonSearchFilters.value,
      order_by: sortOrder.value,
      limit_page_length: itemsPerPage.value,
      limit_start: 0,
    })

    // Also reload count with new filters
    getIssuesCount(nonSearchFilters.value)
  },
  { deep: true },
)

// Watch for search query changes to handle clearing the search
watch(
  searchQuery,
  (newSearchQuery) => {
    // If search is cleared and we were in suggestion mode, return to normal view
    if (!newSearchQuery && isUsingSuggestionFilter.value) {
      clearSuggestionFilter()
    }
  }
)

// Note: We intentionally do NOT watch debouncedSearchQuery for table updates
// The table should only update when:
// 1. A suggestion is explicitly selected (handled in handleSuggestionSelected)
// 2. Other filters are changed (handled in the watcher above)
// 3. Search is cleared while in suggestion mode (handled in the searchQuery watcher above)

onMounted(() => {
  // Load initial data with pagination parameters (excluding search filters)
  reloadIssues({
    filters: nonSearchFilters.value,
    order_by: sortOrder.value,
    limit_page_length: itemsPerPage.value,
    limit_start: 0,
  })

  // Load initial count
  getIssuesCount(nonSearchFilters.value)

  // Listen for list update events from the composable
  window.addEventListener('issueListUpdated', (event) => {
    const { count, documents } = event.detail
    addNotification({
      type: 'info',
      title: 'List Updated',
      message: `${count} issue${count > 1 ? 's' : ''} updated: ${documents.slice(0, 3).join(', ')}${documents.length > 3 ? '...' : ''}`,
      timestamp: new Date()
    })
  })
})

onUnmounted(() => {
  // Clean up event listener
  window.removeEventListener('issueListUpdated', () => { })
})

</script>