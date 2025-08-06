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
      <IssueStats :issues="issues" :activeFilter="currentStatFilter" @filter-changed="handleStatFilterChanged" />

      <!-- Search and Filters -->
      <IssueFilters v-model:searchQuery="searchQuery" v-model:filters="filters" :statusOptions="statusOptions"
        :priorityOptions="priorityOptions" :assigneeOptions="assigneeOptions" :tagsOptions="tagsOptions"
        :issues="allIssues" :filteredCount="totalIssues" @suggestion-selected="handleSuggestionSelected" 
        @filters-applied="handleFiltersApplied" />

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
            <div v-if="pendingDocumentRefreshes.length > 0"
              class="absolute -top-2 -right-2 bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium animate-bounce">
              {{ pendingDocumentRefreshes.length > 9 ? '9+' : pendingDocumentRefreshes.length }}
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
import { computed, onMounted, onUnmounted, ref, watch, shallowRef, markRaw } from "vue"
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
  filterIssuesByStat,
  getStatFilterCount,
  statFilterResource,
  statFilterCountResource,
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

// Suggestion filtering has been removed - suggestions now open issues in new tabs

// State to track if we're using stat-based filtering
const isUsingStatFilter = ref(false)
const currentStatFilter = ref('team_tickets') // Default to team tickets

// Optimized refresh function using unified approach
const refreshCurrentView = () => {
  console.log('Refreshing current view:', { 
    isUsingStatFilter: isUsingStatFilter.value, 
    currentStatFilter: currentStatFilter.value,
    hasCustomFilters: complexFilters.value && complexFilters.value.length > 0
  })

  // Preserve current pagination when refreshing
  const currentParams = {
    limit_page_length: itemsPerPage.value,
    limit_start: (currentPage.value - 1) * itemsPerPage.value,
    order_by: sortOrder.value,
  }

  if (isUsingStatFilter.value) {
    // Refresh using stat filter mode with current pagination
    if (complexFilters.value && complexFilters.value.length > 0) {
      currentParams.filters = JSON.stringify(complexFilters.value)
    }
    
    // Use Promise.all for better performance during refresh
    Promise.all([
      filterIssuesByStat(currentStatFilter.value, currentParams),
      complexFilters.value && complexFilters.value.length > 0 
        ? getStatFilterCount(currentStatFilter.value, JSON.stringify(complexFilters.value))
        : getStatFilterCount(currentStatFilter.value)
    ]).then(() => {
      console.log('Stat filter view refreshed successfully')
    }).catch((error) => {
      console.error('Error refreshing stat filter view:', error)
    })
  } else {
    // Refresh using regular filter mode
    Promise.all([
      reloadIssues({
        filters: JSON.stringify(complexFilters.value),
        ...currentParams,
      }),
      getIssuesCount(JSON.stringify(complexFilters.value))
    ]).then(() => {
      console.log('Regular filter view refreshed successfully')
    }).catch((error) => {
      console.error('Error refreshing regular filter view:', error)
    })
  }
}

// Realtime list updates composable (Frappe-style)
const {
  pendingDocumentRefreshes,
  realtimeEventsSetup,
  manualRefresh: originalManualRefresh
} = useIssueListUpdates(() => {
  // Return current parameters for realtime updates
  return {
    filters: nonSearchFilters.value,
    order_by: sortOrder.value,
    limit_page_length: itemsPerPage.value,
    limit_start: (currentPage.value - 1) * itemsPerPage.value,
  }
}, refreshCurrentView)

// Override manual refresh to use our custom refresh function
const manualRefresh = () => {
  refreshCurrentView()
}

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
  if (isUsingStatFilter.value) {
    return statFilterResource.data || []
  }
  return issuesResource.data || []
})

const totalIssues = computed(() => {
  if (isUsingStatFilter.value) {
    return statFilterCountResource.data || 0
  }
  return issuesCountResource.data || 0
})

const isLoading = computed(() => {
  if (isUsingStatFilter.value) {
    return statFilterResource.loading
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

// Handle suggestion selection from search - now just opens issue in new tab
const handleSuggestionSelected = (suggestion) => {
  // Suggestions now open issues in new tabs - no filtering needed
  // The CustomSearchBox component handles opening the issue in a new tab
}

// Handle complex filter objects from IssueFilters component
const complexFilters = ref([])

const handleFiltersApplied = (filterArray) => {
  console.log('Filters applied:', filterArray)
  
  // Store the complex filters
  complexFilters.value = filterArray
  
  // Reset to first page when applying new filters
  currentPage.value = 1
  
  // Apply the current filtering logic based on the situation
  if (filterArray && filterArray.length > 0) {
    // User has applied custom filters
    if (isUsingStatFilter.value) {
      // User is on a stat card and applying additional filters
      console.log('Applying custom filters on top of card filter:', currentStatFilter.value)
      applyCardFilterWithCustomFilters(currentStatFilter.value)
    } else {
      // User is applying custom filters without any stat card
      console.log('Applying custom filters in regular mode')
      applyCustomFiltersOnly()
    }
  } else {
    // No filters applied - return to default team tickets view
    console.log('No filters applied, returning to default view')
    returnToDefaultView()
  }
}

// Function to apply custom filters without stat card
const applyCustomFiltersOnly = () => {
  isUsingStatFilter.value = false
  currentStatFilter.value = 'team_tickets'
  
  // Use Promise.all for better performance
  Promise.all([
    reloadIssues({
      filters: JSON.stringify(complexFilters.value),
      order_by: sortOrder.value,
      limit_page_length: itemsPerPage.value,
      limit_start: 0,
    }),
    getIssuesCount(JSON.stringify(complexFilters.value))
  ]).then(() => {
    console.log('Custom filters applied successfully')
  }).catch((error) => {
    console.error('Error applying custom filters:', error)
  })
}

// Function to return to default view
const returnToDefaultView = () => {
  isUsingStatFilter.value = true
  currentStatFilter.value = 'team_tickets'
  
  // Use the unified function for consistency
  applyCardFilterWithCustomFilters('team_tickets')
}

// Handle stat filter changes from IssueStats component
const handleStatFilterChanged = (statType) => {
  console.log('Card clicked:', statType, 'Current filters:', complexFilters.value)
  
  // Set stat filter mode
  isUsingStatFilter.value = true
  currentStatFilter.value = statType
  
  // Clear search query
  searchQuery.value = ""
  
  // Reset to first page
  currentPage.value = 1
  
  // Always apply the card filter with any existing custom filters
  applyCardFilterWithCustomFilters(statType)
}

// Unified function to apply card filter with custom filters
const applyCardFilterWithCustomFilters = (statType) => {
  // Build parameters for stat filtering
  const statParams = {
    limit_page_length: itemsPerPage.value,
    limit_start: 0,
    order_by: sortOrder.value,
  }
  
  // Always include custom filters if they exist
  if (complexFilters.value && complexFilters.value.length > 0) {
    statParams.filters = JSON.stringify(complexFilters.value)
    console.log('Applying card filter with custom filters:', statType, complexFilters.value)
  } else {
    console.log('Applying card filter without custom filters:', statType)
  }
  
  // Make both API calls simultaneously for better performance
  Promise.all([
    filterIssuesByStat(statType, statParams),
    complexFilters.value && complexFilters.value.length > 0 
      ? getStatFilterCount(statType, JSON.stringify(complexFilters.value))
      : getStatFilterCount(statType)
  ]).then(() => {
    console.log('Card filter applied successfully')
  }).catch((error) => {
    console.error('Error applying card filter:', error)
  })
}

// Function to clear stat filter and return to normal view
const clearStatFilter = () => {
  isUsingStatFilter.value = false
  currentStatFilter.value = 'team_tickets'
  
  // Reset to first page
  currentPage.value = 1
  
  // Reload with normal filters
  reloadIssues({
    filters: nonSearchFilters.value,
    order_by: sortOrder.value,
    limit_page_length: itemsPerPage.value,
    limit_start: 0,
  })
  
  // Reload count
  getIssuesCount(nonSearchFilters.value)
}

// Memoized filter options to prevent unnecessary re-computations
// These are static or rarely changing, so we can use shallowRef for better performance
const priorityOptions = shallowRef(markRaw(getPriorityOptions()))
const tagsOptions = shallowRef(markRaw(getIssueTypeOptions()))
const statusOptions = shallowRef(markRaw(getStatusOptions()))

// Memoized assignee options with caching based on issues length
let assigneeOptionsCache = null
let lastIssuesLength = 0
const assigneeOptions = computed(() => {
  const currentLength = allIssues.value.length
  
  // Return cached options if issues length hasn't changed
  if (assigneeOptionsCache && lastIssuesLength === currentLength) {
    return assigneeOptionsCache
  }
  
  // Recalculate and cache
  assigneeOptionsCache = markRaw(getAssigneeOptions(allIssues.value))
  lastIssuesLength = currentLength
  
  return assigneeOptionsCache
})

// Pagination state
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Optimized pagination handler using unified approach
const handlePageChange = ({ page, itemsPerPage: newItemsPerPage, offset }) => {
  console.log('Page change:', { page, newItemsPerPage, offset })
  
  currentPage.value = page
  itemsPerPage.value = newItemsPerPage

  // Build pagination parameters
  const paginationParams = {
    limit_page_length: newItemsPerPage,
    limit_start: offset,
    order_by: sortOrder.value,
  }

  if (isUsingStatFilter.value) {
    // Use stat-based filtering for pagination
    if (complexFilters.value && complexFilters.value.length > 0) {
      paginationParams.filters = JSON.stringify(complexFilters.value)
    }
    
    // Only need to reload data, count doesn't change during pagination
    filterIssuesByStat(currentStatFilter.value, paginationParams)
      .then(() => {
        console.log('Pagination completed successfully (stat filter)')
      }).catch((error) => {
        console.error('Error during pagination (stat filter):', error)
      })
  } else {
    // Use regular filtering for pagination
    reloadIssues({
      filters: JSON.stringify(complexFilters.value),
      ...paginationParams,
    }).then(() => {
      console.log('Pagination completed successfully (regular filter)')
    }).catch((error) => {
      console.error('Error during pagination (regular filter):', error)
    })
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

// Note: Filter changes are now handled by the IssueFilters component through handleFiltersApplied()
// This provides better performance and more precise control over when filtering occurs
// No more watchers or debouncing needed - filtering happens only on explicit user actions

// Search query changes no longer trigger table updates since suggestions open in new tabs

onMounted(() => {
  console.log('IssueTracker mounted, initializing with default view')
  
  // Start with default stat filter (Team Tickets) active
  isUsingStatFilter.value = true
  currentStatFilter.value = 'team_tickets'
  
  // Load initial data using unified approach
  applyCardFilterWithCustomFilters('team_tickets')

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