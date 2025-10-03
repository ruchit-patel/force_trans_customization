<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header with Navigation -->
    <div class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div class="flex items-center space-x-4">
            <h1 class="text-2xl font-bold text-gray-900">Ticket Tracker</h1>
            <nav class="flex space-x-4">
              <router-link to="/"
                class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                active-class="bg-blue-100 text-blue-700"
                inactive-class="text-gray-600 hover:text-gray-900">
                Tickets
              </router-link>
              <router-link to="/sent-emails"
                class="bg-blue-100 text-blue-700 px-3 py-2 rounded-md text-sm font-medium"
                active-class="bg-blue-100 text-blue-700"
                inactive-class="text-gray-600 hover:text-gray-900">
                Sent Emails
              </router-link>
              <a href="/app/support"
                class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                Desk
              </a>
              <a href="/intro"
                class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                Wiki
              </a>
            </nav>
          </div>
          <div class="flex items-center space-x-4">
            <Button @click="showComposeEmailDialog = true" variant="solid" size="sm">
              <template #prefix>
                <FeatherIcon name="mail" class="w-4 h-4" />
              </template>
              Compose Email
            </Button>
            <span class="text-sm text-gray-600">{{ session.user }}</span>
            <Button @click="session.logout.submit()" variant="outline" size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Page Header -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-semibold text-gray-900">Sent Emails</h2>
            <p class="text-sm text-gray-500 mt-1">View all newsletters sent, scheduled, or saved as drafts</p>
          </div>
          <Button @click="refreshNewsletters" :loading="isLoading">
            <template #prefix>
              <FeatherIcon name="refresh-cw" class="w-4 h-4" />
            </template>
            Refresh
          </Button>
        </div>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
      <div class="flex items-center gap-4">
        <!-- Search -->
        <div class="flex-1 max-w-md">
          <div class="relative">
            <FeatherIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by subject or sender..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @input="debouncedSearch"
            />
          </div>
        </div>

        <!-- Status Filter -->
        <div class="w-48">
          <select
            v-model="statusFilter"
            @change="applyFilters"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="sent">Sent</option>
            <option value="scheduled">Scheduled</option>
            <option value="draft">Draft</option>
          </select>
        </div>

        <!-- Date Range Filter -->
        <div class="w-48">
          <select
            v-model="dateFilter"
            @change="applyFilters"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Time</option>
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="year">This Year</option>
          </select>
        </div>

        <!-- Clear Filters -->
        <Button v-if="hasActiveFilters" @click="clearFilters" variant="ghost">
          <template #prefix>
            <FeatherIcon name="x" class="w-4 h-4" />
          </template>
          Clear
        </Button>
      </div>

      <!-- Active Filters Summary -->
      <div v-if="hasActiveFilters" class="mt-3 flex items-center gap-2 text-sm text-gray-600">
        <span class="font-medium">Active filters:</span>
        <span v-if="statusFilter !== 'all'" class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 rounded">
          Status: {{ statusFilter }}
        </span>
        <span v-if="dateFilter !== 'all'" class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 rounded">
          Date: {{ dateFilter }}
        </span>
        <span v-if="searchQuery" class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 rounded">
          Search: "{{ searchQuery }}"
        </span>
        <span class="text-gray-500">{{ totalCount }} results</span>
      </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && newsletters.length === 0" class="flex items-center justify-center flex-1">
      <div class="text-center">
        <LoadingIndicator class="w-8 h-8 mx-auto mb-4" />
        <p class="text-gray-500">Loading newsletters...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!isLoading && newsletters.length === 0" class="flex items-center justify-center flex-1">
      <div class="text-center max-w-md">
        <FeatherIcon name="mail" class="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No newsletters found</h3>
        <p class="text-gray-500 mb-6">
          {{ hasActiveFilters ? 'No newsletters match your filters. Try adjusting your search.' : 'You haven\'t sent any newsletters yet. Create one from the Issues page.' }}
        </p>
      </div>
    </div>

    <!-- Newsletter List -->
    <div v-else class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div>
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subject
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Recipients
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sent By
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="newsletter in newsletters" :key="newsletter.name" class="hover:bg-gray-50">
                <td class="px-6 py-4">
                  <div class="flex items-center">
                    <FeatherIcon name="mail" class="w-4 h-4 text-gray-400 mr-3" />
                    <div>
                      <div class="text-sm font-medium text-gray-900">
                        {{ newsletter.subject }}
                      </div>
                      <div class="text-xs text-gray-500">
                        {{ newsletter.name }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusBadgeClass(newsletter)" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">
                    {{ getStatusText(newsletter) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ newsletter.total_recipients || 0 }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">{{ newsletter.sender_name || 'Unknown' }}</div>
                  <div class="text-xs text-gray-500">{{ newsletter.sender_email }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">
                    {{ formatDate(newsletter.email_sent_at || newsletter.schedule_send || newsletter.modified) }}
                  </div>
                  <div class="text-xs text-gray-500">
                    {{ formatTime(newsletter.email_sent_at || newsletter.schedule_send || newsletter.modified) }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button @click="viewNewsletter(newsletter)" class="text-blue-600 hover:text-blue-900 mr-4">
                    View
                  </button>
                  <button v-if="!newsletter.email_sent" @click="deleteNewsletter(newsletter)" class="text-red-600 hover:text-red-900">
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="mt-4 flex items-center justify-between bg-white px-6 py-3 rounded-lg shadow">
          <div class="flex items-center gap-4">
            <span class="text-sm text-gray-700">
              Showing <span class="font-medium">{{ startIndex + 1 }}</span> to <span class="font-medium">{{ endIndex }}</span> of <span class="font-medium">{{ totalCount }}</span> results
            </span>
            <select
              v-model="pageSize"
              @change="changePageSize"
              class="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option :value="10">10 per page</option>
              <option :value="20">20 per page</option>
              <option :value="50">50 per page</option>
              <option :value="100">100 per page</option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <Button
              @click="goToPage(currentPage - 1)"
              :disabled="currentPage === 1"
              variant="ghost"
              size="sm"
            >
              <template #prefix>
                <FeatherIcon name="chevron-left" class="w-4 h-4" />
              </template>
              Previous
            </Button>

            <div class="flex items-center gap-1">
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="goToPage(page)"
                :class="[
                  'px-3 py-1 text-sm rounded',
                  page === currentPage
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                ]"
              >
                {{ page }}
              </button>
            </div>

            <Button
              @click="goToPage(currentPage + 1)"
              :disabled="currentPage === totalPages"
              variant="ghost"
              size="sm"
            >
              Next
              <template #suffix>
                <FeatherIcon name="chevron-right" class="w-4 h-4" />
              </template>
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Compose Email Dialog -->
    <ComposeEmailDialog
      v-model:show="showComposeEmailDialog"
      @email-sent="handleEmailSent"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Button, FeatherIcon, LoadingIndicator } from 'frappe-ui'
import { call } from 'frappe-ui'
import { session } from '../data/session'
import ComposeEmailDialog from '../components/ComposeEmailDialog.vue'

const newsletters = ref([])
const isLoading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('all')
const dateFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const showComposeEmailDialog = ref(false)

let searchTimeout = null

const hasActiveFilters = computed(() => {
  return statusFilter.value !== 'all' || dateFilter.value !== 'all' || searchQuery.value !== ''
})

const totalPages = computed(() => {
  return Math.ceil(totalCount.value / pageSize.value)
})

const startIndex = computed(() => {
  return (currentPage.value - 1) * pageSize.value
})

const endIndex = computed(() => {
  return Math.min(startIndex.value + pageSize.value, totalCount.value)
})

const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)

  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

const getDateFilter = () => {
  const now = new Date()
  let startDate = null

  switch (dateFilter.value) {
    case 'today':
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      break
    case 'week':
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7)
      break
    case 'month':
      startDate = new Date(now.getFullYear(), now.getMonth(), 1)
      break
    case 'year':
      startDate = new Date(now.getFullYear(), 0, 1)
      break
  }

  if (startDate) {
    return startDate.toISOString().split('T')[0] + ' 00:00:00'
  }

  return null
}

const buildFilters = () => {
  const filters = []

  // Status filter
  if (statusFilter.value === 'sent') {
    filters.push(['email_sent', '=', 1])
  } else if (statusFilter.value === 'scheduled') {
    filters.push(['schedule_sending', '=', 1])
    filters.push(['email_sent', '=', 0])
  } else if (statusFilter.value === 'draft') {
    filters.push(['email_sent', '=', 0])
    filters.push(['schedule_sending', '=', 0])
  }

  // Date filter
  const dateFilterValue = getDateFilter()
  if (dateFilterValue) {
    filters.push(['modified', '>=', dateFilterValue])
  }

  // Search filter
  if (searchQuery.value) {
    filters.push([
      ['subject', 'like', `%${searchQuery.value}%`],
      'or',
      ['sender_name', 'like', `%${searchQuery.value}%`],
      'or',
      ['sender_email', 'like', `%${searchQuery.value}%`]
    ])
  }

  return filters
}

const loadNewsletters = async () => {
  isLoading.value = true
  try {
    console.log('Loading newsletters with filters...')

    const filters = buildFilters()

    const response = await call('frappe.client.get_list', {
      doctype: 'Newsletter',
      fields: [
        'name',
        'subject',
        'sender_name',
        'sender_email',
        'email_sent',
        'email_sent_at',
        'schedule_sending',
        'schedule_send',
        'total_recipients',
        'total_views',
        'modified',
        'owner'
      ],
      filters: filters,
      order_by: 'modified desc',
      limit_start: startIndex.value,
      limit_page_length: pageSize.value
    })

    // Get total count
    const countResponse = await call('frappe.client.get_count', {
      doctype: 'Newsletter',
      filters: filters
    })

    newsletters.value = response || []
    totalCount.value = countResponse || 0

    console.log(`Loaded ${newsletters.value.length} newsletters (${totalCount.value} total)`)
  } catch (error) {
    console.error('Error loading newsletters:', error)
    newsletters.value = []
    totalCount.value = 0
  } finally {
    isLoading.value = false
  }
}

const refreshNewsletters = () => {
  currentPage.value = 1
  loadNewsletters()
}

const applyFilters = () => {
  currentPage.value = 1
  loadNewsletters()
}

const debouncedSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    applyFilters()
  }, 500)
}

const clearFilters = () => {
  searchQuery.value = ''
  statusFilter.value = 'all'
  dateFilter.value = 'all'
  currentPage.value = 1
  loadNewsletters()
}

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadNewsletters()
  }
}

const changePageSize = () => {
  currentPage.value = 1
  loadNewsletters()
}

const getStatusText = (newsletter) => {
  if (newsletter.email_sent) {
    return 'Sent'
  } else if (newsletter.schedule_sending) {
    return 'Scheduled'
  } else {
    return 'Draft'
  }
}

const getStatusBadgeClass = (newsletter) => {
  if (newsletter.email_sent) {
    return 'bg-green-100 text-green-800'
  } else if (newsletter.schedule_sending) {
    return 'bg-blue-100 text-blue-800'
  } else {
    return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const formatTime = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const viewNewsletter = (newsletter) => {
  // Open newsletter in Frappe desk
  window.open(`/app/newsletter/${newsletter.name}`, '_blank')
}

const deleteNewsletter = async (newsletter) => {
  if (!confirm(`Are you sure you want to delete "${newsletter.subject}"?`)) {
    return
  }

  try {
    await call('frappe.client.delete', {
      doctype: 'Newsletter',
      name: newsletter.name
    })

    // Reload the current page
    loadNewsletters()

    console.log(`Deleted newsletter: ${newsletter.name}`)
  } catch (error) {
    console.error('Error deleting newsletter:', error)
    alert(`Failed to delete newsletter: ${error.message || error}`)
  }
}

const handleEmailSent = (emailData) => {
  // Close the dialog
  showComposeEmailDialog.value = false

  // Refresh the newsletter list to show the newly sent/saved email
  refreshNewsletters()
}

onMounted(() => {
  loadNewsletters()
})
</script>
