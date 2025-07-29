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

      <!-- Issues Table Placeholder -->
      <div class="bg-white rounded-lg shadow-sm border">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">Issues</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Issue ID
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Assignee
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Project
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tags
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created At
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <!-- Loading state -->
              <tr v-if="isLoading">
                <td colspan="8" class="px-6 py-12 text-center text-gray-500">
                  <div class="flex items-center justify-center">
                    <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    <span class="ml-2">Loading issues...</span>
                  </div>
                </td>
              </tr>
              <!-- No data state -->
              <tr v-else-if="!issues.length">
                <td colspan="8" class="px-6 py-12 text-center text-gray-500">
                  No issues found.
                </td>
              </tr>
              <!-- Issues data -->
              <tr v-else v-for="issue in issues" :key="issue.name" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                  {{ issue.name }}
                </td>
                <td class="px-6 py-4 text-sm text-gray-900">
                  <div class="max-w-xs truncate">{{ issue.subject }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="{
                    'bg-blue-100 text-blue-800': issue.status === 'Open',
                    'bg-yellow-100 text-yellow-800': issue.status === 'Replied',
                    'bg-orange-100 text-orange-800': issue.status === 'On Hold',
                    'bg-green-100 text-green-800': issue.status === 'Resolved',
                    'bg-gray-100 text-gray-800': issue.status === 'Closed'
                  }" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                    {{ issue.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="{
                    'bg-red-100 text-red-800': issue.priority === 'High' || issue.priority === 'Critical',
                    'bg-yellow-100 text-yellow-800': issue.priority === 'Medium',
                    'bg-green-100 text-green-800': issue.priority === 'Low'
                  }" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                    {{ issue.priority || 'Medium' }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ issue.raised_by || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ issue.project || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <span v-if="issue.issue_type"
                    class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                    {{ issue.issue_type }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ new Date(issue.creation).toLocaleDateString() }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Placeholder -->
        <div class="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div class="text-sm text-gray-700">
            Showing 0 to 0 of 0 results
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