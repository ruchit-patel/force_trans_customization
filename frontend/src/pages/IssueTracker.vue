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
      <IssueFilters
        v-model:searchQuery="searchQuery"
        v-model:filters="filters"
        :statusOptions="statusOptions"
        :priorityOptions="priorityOptions"
        :assigneeOptions="assigneeOptions"
        :tagsOptions="tagsOptions"
      />

      <!-- Issues Table -->
      <IssueTable
        :issues="issues"
        :loading="isLoading"
        :sortField="currentSortField"
        :sortDirection="currentSortDirection"
        @sort="handleSort"
      />

      <!-- Pagination -->
      <IssuePagination
        v-model:currentPage="currentPage"
        v-model:itemsPerPage="itemsPerPage"
        :totalItems="totalIssues"
        @pageChange="handlePageChange"
      />

      <!-- Compact Real-time Status Icons (Vertical) -->
      <div class="fixed top-20 right-4 flex flex-col space-y-2">
        <!-- Connection Status -->
        <div 
          class="group relative bg-white rounded-full shadow-lg border p-2 hover:shadow-xl transition-all duration-200"
          :title="realtimeEventsSetup ? 'Real-time updates active' : 'Real-time updates disabled'"
        >
          <!-- Connection Icon with Status -->
          <div class="relative">
            <FeatherIcon 
              :name="realtimeEventsSetup ? 'wifi' : 'wifi-off'" 
              :class="[
                'h-5 w-5 transition-colors duration-200',
                realtimeEventsSetup ? 'text-green-600' : 'text-red-500'
              ]"
            />
            <!-- Status Dot -->
            <div 
              :class="[
                'absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white',
                realtimeEventsSetup 
                  ? 'bg-green-500 animate-pulse' 
                  : 'bg-red-500'
              ]"
            ></div>
            <!-- Pending Updates Badge -->
            <div 
              v-if="pendingDocumentRefreshes > 0"
              class="absolute -top-2 -right-2 bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium animate-bounce"
            >
              {{ pendingDocumentRefreshes > 9 ? '9+' : pendingDocumentRefreshes }}
            </div>
          </div>
        </div>

        <!-- Manual Refresh Button -->
        <button 
          @click="manualRefresh"
          class="group bg-white rounded-full shadow-lg border p-2 hover:shadow-xl hover:bg-blue-50 transition-all duration-200 active:scale-95"
          title="Manual refresh"
        >
          <FeatherIcon 
            name="refresh-cw" 
            class="h-5 w-5 text-gray-600 group-hover:text-blue-600 group-active:rotate-180 transition-all duration-300"
          />
        </button>
      </div>
    </div>

    <!-- Real-time Notifications -->
    <RealTimeNotifications
      :notifications="notifications"
      @remove="removeNotification"
    />
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

// Realtime list updates composable (Frappe-style)
const {
	pendingDocumentRefreshes,
	realtimeEventsSetup,
	manualRefresh
} = useIssueListUpdates()

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
const allIssues = computed(() => issuesResource.data || [])
const totalIssues = computed(() => issuesCountResource.data || 0)
const isLoading = computed(() => issuesResource.loading)

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

	// Reload issues with pagination parameters
	reloadIssues({
		filters: apiFilters.value,
		order_by: sortOrder.value,
		limit_page_length: newItemsPerPage,
		limit_start: offset,
	})

	// Also reload count with current filters
	getIssuesCount(apiFilters.value)
}

// Watch for filter changes and reload data from server when needed
watch(
	[debouncedSearchQuery, apiFilters, sortOrder],
	() => {
		// Reset to first page when filters change
		currentPage.value = 1

		// Reload issues with new filters and sort order
		reloadIssues({
			filters: apiFilters.value,
			order_by: sortOrder.value,
			limit_page_length: itemsPerPage.value,
			limit_start: 0,
		})

		// Also reload count with new filters
		getIssuesCount(apiFilters.value)
	},
	{ deep: true },
)

onMounted(() => {
	// Load initial data with pagination parameters
	reloadIssues({
		filters: apiFilters.value,
		order_by: sortOrder.value,
		limit_page_length: itemsPerPage.value,
		limit_start: 0,
	})

	// Load initial count
	getIssuesCount(apiFilters.value)
	
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
	window.removeEventListener('issueListUpdated', () => {})
})

</script>