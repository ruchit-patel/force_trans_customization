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

      <!-- Pagination Placeholder -->
      <div class="bg-white rounded-lg shadow-sm border mt-4">
        <div class="px-6 py-4 flex items-center justify-between">
          <div class="text-sm text-gray-700">
            Showing {{ issues.length }} of {{ totalIssues }} results
          </div>
          <div class="flex space-x-2">
            <Button theme="gray" variant="outline" size="sm" disabled>
              Previous
            </Button>
            <Button theme="gray" variant="outline" size="sm" disabled>
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { session } from "../data/session"
import {
  issuesResource,
  issuesCountResource,
  reloadIssues,
  getPriorityOptions,
  getIssueTypeOptions,
  getProjectOptions,
  getStatusOptions
} from "../data/issues"
import { computed, onMounted, watch } from "vue"
import IssueStats from "../components/IssueStats.vue"
import IssueFilters from "../components/IssueFilters.vue"
import IssueTable from "../components/IssueTable.vue"
import { useIssueFilters } from "../composables/useIssueFilters"

// Use the filtering composable
const {
  searchQuery,
  filters,
  debouncedSearchQuery,
  apiFilters,
  sortOrder,
  filterIssues,
  getAssigneeOptions
} = useIssueFilters()

// Computed properties for displaying data
const allIssues = computed(() => issuesResource.data || [])
const totalIssues = computed(() => issuesCountResource.data || 0)
const isLoading = computed(() => issuesResource.loading)

// Apply client-side filtering to issues
const issues = computed(() => filterIssues(allIssues.value))

// Sort functionality
const currentSortField = computed(() => {
  const order = sortOrder.value || 'creation desc'
  return order.split(' ')[0]
})

const currentSortDirection = computed(() => {
  const order = sortOrder.value || 'creation desc'
  return order.split(' ')[1] || 'desc'
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
const projectOptions = computed(() => getProjectOptions())
const statusOptions = computed(() => getStatusOptions())
const assigneeOptions = computed(() => getAssigneeOptions(allIssues.value))

// Watch for filter changes and reload data from server when needed
watch([debouncedSearchQuery, apiFilters, sortOrder], () => {
  // Reload issues with new filters and sort order
  reloadIssues({
    filters: apiFilters.value,
    order_by: sortOrder.value
  })
}, { deep: true })

onMounted(() => {
  // Resources will auto-fetch due to auto: true, but we can manually trigger if needed
  if (!issuesResource.data) {
    issuesResource.fetch()
  }
  if (!issuesCountResource.data) {
    issuesCountResource.fetch()
  }
})
</script>