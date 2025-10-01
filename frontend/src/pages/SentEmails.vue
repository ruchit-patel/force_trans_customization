<template>
  <div class="h-full flex flex-col bg-gray-50">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold text-gray-900">Sent Emails</h1>
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
        <p class="text-gray-500 mb-6">You haven't sent any newsletters yet. Create one from the Issues page.</p>
      </div>
    </div>

    <!-- Newsletter List -->
    <div v-else class="flex-1 overflow-auto p-6">
      <div class="max-w-7xl mx-auto">
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Button, FeatherIcon, LoadingIndicator } from 'frappe-ui'
import { call } from 'frappe-ui'

const newsletters = ref([])
const isLoading = ref(false)

const loadNewsletters = async () => {
  isLoading.value = true
  try {
    console.log('Loading newsletters...')

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
      order_by: 'modified desc',
      limit_page_length: 100
    })

    newsletters.value = response || []
    console.log(`Loaded ${newsletters.value.length} newsletters`)
  } catch (error) {
    console.error('Error loading newsletters:', error)
    newsletters.value = []
  } finally {
    isLoading.value = false
  }
}

const refreshNewsletters = () => {
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

    // Remove from list
    newsletters.value = newsletters.value.filter(n => n.name !== newsletter.name)

    console.log(`Deleted newsletter: ${newsletter.name}`)
  } catch (error) {
    console.error('Error deleting newsletter:', error)
    alert(`Failed to delete newsletter: ${error.message || error}`)
  }
}

onMounted(() => {
  loadNewsletters()
})
</script>
