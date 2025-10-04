<template>
  <div v-if="isDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black bg-opacity-50" @click="closeDialog"></div>

    <!-- Dialog -->
    <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Select Email Groups</h2>
        <button @click="closeDialog" class="text-gray-400 hover:text-gray-600">
          <FeatherIcon name="x" class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
    <div class="space-y-4">
      <!-- Search Groups -->
      <div class="relative">
        <FeatherIcon name="search" class="w-4 h-4 text-gray-400 absolute left-3 top-3" />
        <input
          ref="searchInput"
          v-model="searchQuery"
          type="text"
          placeholder="Search email groups..."
          class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Groups List -->
      <div class="max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
        <div v-if="isLoading" class="p-8 text-center">
          <div class="flex items-center justify-center">
            <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500 mr-2"></div>
            Loading email groups...
          </div>
        </div>

        <div v-else-if="filteredGroups.length === 0" class="p-8 text-center text-gray-500">
          <FeatherIcon name="inbox" class="w-8 h-8 mx-auto mb-2 text-gray-300" />
          <p>No email groups found</p>
          <p class="text-xs mt-1">Create email groups in the system to see them here</p>
        </div>

        <div v-else class="divide-y divide-gray-200">
          <div
            v-for="group in filteredGroups"
            :key="group.name"
            class="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            @click="toggleGroup(group)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <input
                  type="checkbox"
                  :checked="isGroupSelected(group)"
                  @change="toggleGroup(group)"
                  @click.stop
                  class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                />
                <div>
                  <div class="font-medium text-gray-900">{{ group.title || group.name }}</div>
                  <div class="text-sm text-gray-500">
                    {{ group.email_count || 0 }} recipients
                  </div>
                  <div v-if="group.description" class="text-xs text-gray-400 mt-1">
                    {{ group.description }}
                  </div>
                </div>
              </div>
              <div class="text-right">
                <div class="text-sm text-gray-500">
                  Created: {{ formatDate(group.creation) }}
                </div>
                <div v-if="group.modified !== group.creation" class="text-xs text-gray-400">
                  Modified: {{ formatDate(group.modified) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Selected Groups Summary -->
      <div v-if="selectedGroups.length > 0" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 class="font-medium text-blue-900 mb-2">Selected Groups ({{ selectedGroups.length }})</h4>
        <div class="space-y-1">
          <div
            v-for="group in selectedGroups"
            :key="group.name"
            class="flex items-center justify-between text-sm"
          >
            <span class="text-blue-800">{{ group.title || group.name }}</span>
            <span class="text-blue-600">{{ group.email_count || 0 }} recipients</span>
          </div>
        </div>
        <div class="mt-2 pt-2 border-t border-blue-200">
          <span class="font-medium text-blue-900">
            Total Recipients: {{ totalSelectedRecipients }}
          </span>
        </div>
      </div>
    </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
        <Button @click="closeDialog" variant="outline">
          Cancel
        </Button>
        <Button @click="selectGroups" variant="solid">
          Done
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineEmits, defineProps } from 'vue'
import { Button, FeatherIcon, call } from 'frappe-ui'

// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['update:show', 'groups-selected', 'dialog-closed'])

// Dialog state
const isDialogOpen = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

// Component state
const searchInput = ref(null)
const searchQuery = ref('')
const isLoading = ref(false)
const emailGroups = ref([])
const selectedGroups = ref([])
const groupMembersCache = ref({})

// Computed properties
const filteredGroups = computed(() => {
  if (!searchQuery.value) {
    return emailGroups.value
  }

  const query = searchQuery.value.toLowerCase()
  return emailGroups.value.filter(group =>
    group.name.toLowerCase().includes(query) ||
    (group.description && group.description.toLowerCase().includes(query))
  )
})

const totalSelectedRecipients = computed(() => {
  return selectedGroups.value.reduce((total, group) => total + (group.email_count || 0), 0)
})

// Methods
const loadEmailGroups = async () => {
  isLoading.value = true
  try {
    console.log('Loading email groups from Frappe...')

    // Fetch Email Groups from Frappe
    const response = await call('frappe.client.get_list', {
      doctype: 'Email Group',
      fields: ['name', 'title', 'total_subscribers', 'creation', 'modified'],
      filters: [
        // Exclude temporary groups
        ['title', 'not like', 'temp-grp-%']
      ],
      order_by: 'modified desc',
      limit_page_length: 100
    })

    console.log('Email Groups loaded:', response)

    // Transform to match our component's expected format
    emailGroups.value = response.map(group => ({
      name: group.name,
      title: group.title || group.name,
      email_count: group.total_subscribers || 0,
      description: '',
      creation: group.creation,
      modified: group.modified,
      emails: [] // Will be loaded on demand when group is selected or expanded
    }))

  } catch (error) {
    console.error('Error loading email groups:', error)
    emailGroups.value = []
  } finally {
    isLoading.value = false
  }
}

const loadGroupMembers = async (groupName) => {
  // Check cache first
  if (groupMembersCache.value[groupName]) {
    return groupMembersCache.value[groupName]
  }

  try {
    console.log('Loading members for group:', groupName)

    const response = await call('frappe.client.get_list', {
      doctype: 'Email Group Member',
      fields: ['email', 'email_group'],
      filters: [
        ['email_group', '=', groupName]
      ],
      limit_page_length: 1000
    })

    const emails = response.map(member => member.email)

    // Cache the result
    groupMembersCache.value[groupName] = emails

    return emails
  } catch (error) {
    console.error('Error loading group members:', error)
    return []
  }
}

const isGroupSelected = (group) => {
  return selectedGroups.value.some(selected => selected.name === group.name)
}

const toggleGroup = async (group) => {
  const index = selectedGroups.value.findIndex(selected => selected.name === group.name)
  if (index > -1) {
    selectedGroups.value.splice(index, 1)
  } else {
    // Load group members when selecting
    const emails = await loadGroupMembers(group.name)
    selectedGroups.value.push({
      ...group,
      emails: emails
    })
  }
}

const selectGroups = () => {
  emit('groups-selected', [...selectedGroups.value])
  closeDialog()
}

const closeDialog = () => {
  isDialogOpen.value = false
  // Reset selections when closing
  selectedGroups.value = []
  searchQuery.value = ''
  // Emit dialog closed event
  emit('dialog-closed')
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch (error) {
    return 'Invalid Date'
  }
}

// Load groups when dialog is opened
onMounted(() => {
  if (props.show) {
    loadEmailGroups()
  }
})

// Watch for dialog opening to load groups
watch(() => props.show, (isOpen) => {
  if (isOpen) {
    loadEmailGroups()
    // Focus on search input after dialog opens
    setTimeout(() => {
      if (searchInput.value) {
        searchInput.value.focus()
      }
    }, 100)
  }
})
</script>