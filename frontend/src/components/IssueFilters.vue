<template>
  <div class="bg-white p-6 rounded-lg shadow-sm border mb-6">
    <!-- Search Section -->
    <div class="mb-6">
      <div class="relative max-w-2xl mx-auto">
        <CustomSearchBox ref="searchBoxRef" :model-value="localSearchQuery" @update:model-value="handleSearchChange"
          @suggestion-selected="handleSuggestionSelected" :issues="issues"
          placeholder="Search issues by title, description, assignee..." class="awesome-search" />
        <div v-if="localSearchQuery" class="absolute top-full left-0 right-0 mt-1 text-sm text-gray-500 text-center">
          Searching in {{ filteredCount }} issues
        </div>
      </div>
    </div>


    <!-- Compact Frappe-style Filter Controls -->
    <div class="border-t border-gray-200 pt-4">
      <div class="flex items-center justify-between">
        <!-- Left side: Filter button and active filters -->
        <div class="flex items-center space-x-3 flex-1">
          <!-- Filters Button -->
          <button @click="showFilterPanel = !showFilterPanel"
            class="inline-flex items-center space-x-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium text-gray-700 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.414A1 1 0 013 6.707V4z"/>
            </svg>
            <span>Filters</span>
            <span v-if="dynamicFilters.length > 0" class="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
              {{ dynamicFilters.length }}
            </span>
          </button>

          <!-- Active Filters - Inline compact display (show applied filters) -->
          <div v-if="appliedFilters.length > 0" class="flex items-center flex-1 overflow-x-auto flex-wrap gap-2">
            <div v-for="(filter, index) in appliedFilters" :key="filter.id" 
              class="flex items-center space-x-1 bg-green-100 border border-green-200 rounded px-2 py-1 text-sm whitespace-nowrap">
              <span class="text-green-800 font-medium">{{ getFieldLabel(filter.field) }}</span>
              <span class="text-green-600">{{ filter.operator }}</span>
              <!-- Special display for tags with colors -->
              <span v-if="filter.field === '_user_tags' && filter.value" 
                :style="getTagStyle(filter.value)"
                class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border">
                {{ filter.value }}
              </span>
              <!-- Regular display for other fields -->
              <span v-else class="text-green-900">{{ filter.value }}</span>
              <button @click="removeAppliedFilter(index)"
                class="text-green-400 hover:text-red-600 ml-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <!-- Show pending changes indicator -->
            <div v-if="hasPendingChanges" class="inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
              <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
              </svg>
              Pending Changes
            </div>
          </div>
        </div>

        <!-- Right side: Clear and Apply buttons -->
        <div class="flex items-center space-x-2 ml-4">
          <!-- Show Clear button if there are any filters OR search query -->
          <button v-if="dynamicFilters.length > 0 || appliedFilters.length > 0 || localSearchQuery" 
            @click="clearAllDynamicFilters"
            class="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            title="Clear all filters and search to show all issues">
            Clear All
          </button>
          <!-- Show Apply button only if there are pending filters -->
          <button v-if="dynamicFilters.length > 0"
            @click="applyFilters"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-md transition-colors',
              hasPendingChanges 
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md' 
                : 'bg-gray-300 text-gray-600 cursor-not-allowed'
            ]"
            :disabled="!hasPendingChanges">
            <span v-if="hasPendingChanges">Apply Filters</span>
            <span v-else>Filters Applied</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Frappe-style Filter Panel -->
    <div v-if="showFilterPanel" class="relative">
      <div class="absolute top-2 left-0 right-0 z-50 bg-white border border-gray-200 rounded-lg shadow-lg" @click.stop>
        <div class="flex">
          <!-- Left Sidebar - Field Selection -->
          <div class="w-48 border-r border-gray-200 bg-gray-50">
            <div class="p-3 border-b border-gray-200">
              <h4 class="text-sm font-medium text-gray-900">Add Filter</h4>
            </div>
            <div class="max-h-64 overflow-y-auto">
              <button v-for="field in availableFields" :key="field.value"
                @click.stop="addNewFilter(field.value)"
                class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors">
                {{ field.label }}
              </button>
            </div>
          </div>

          <!-- Right Panel - Active Filters -->
          <div class="flex-1 min-w-96">
            <div class="p-4">
              <div v-if="dynamicFilters.length === 0" class="text-center py-8 text-gray-500">
                <p class="text-sm">Select a field from the left to add a filter</p>
              </div>
              
              <div v-else class="space-y-3">
                <div v-for="(filter, index) in dynamicFilters" :key="filter.id" 
                  :class="[
                    'flex items-center space-x-3 p-3 rounded border',
                    hasPendingChanges ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                  ]">
                  
                  <!-- Field Name (read-only) -->
                  <div class="w-24 text-sm font-medium text-gray-700">
                    {{ getFieldLabel(filter.field) }}
                  </div>

                  <!-- Operator -->
                  <div class="w-24">
                    <select v-model="filter.operator" @change="updateDynamicFilter(index)"
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                      <option v-for="op in getOperatorOptions(filter.field)" :key="op.value" :value="op.value">
                        {{ op.label }}
                      </option>
                    </select>
                  </div>

                  <!-- Value -->
                  <div class="flex-1">
                    <!-- Special handling for tags with colors -->
                    <div v-if="filter.field === '_user_tags'" class="relative">
                      <select v-model="filter.value" 
                        @change="updateDynamicFilter(index)"
                        class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                        <option value="">Select tag...</option>
                        <option v-for="tag in availableTags" :key="tag.value" :value="tag.value">
                          {{ tag.label }}
                        </option>
                      </select>
                      <!-- Show selected tag with color -->
                      <div v-if="filter.value" class="absolute right-8 top-1/2 transform -translate-y-1/2">
                        <span :style="getTagStyle(filter.value)"
                          class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border">
                          {{ filter.value }}
                        </span>
                      </div>
                    </div>
                    <!-- DateTime inputs for date fields -->
                    <input v-else-if="isDateTimeField(filter.field)"
                      v-model="filter.value"
                      @input="updateDynamicFilter(index)"
                      type="datetime-local"
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />
                    <!-- Date inputs for date fields -->
                    <input v-else-if="isDateField(filter.field)"
                      v-model="filter.value"
                      @input="updateDynamicFilter(index)"
                      type="date"
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />
                    <!-- Multi-select for Users Assigned field -->
                    <div v-else-if="filter.field === 'custom_users_assigned'" class="relative">
                      <div class="flex flex-wrap gap-1 p-2 border border-gray-300 rounded min-h-[32px] focus-within:ring-1 focus-within:ring-blue-500 focus-within:border-blue-500">
                        <span v-for="user in getSelectedUsers(filter.value)" :key="user" 
                          class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full border border-blue-200">
                          {{ user }}
                          <button @click="removeUser(filter, user)" class="ml-1 text-blue-600 hover:text-blue-800">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                          </button>
                        </span>
                        <input 
                          v-model="userInputValue[filter.id]" 
                          @keydown.enter="addUser(filter, $event)"
                          @keydown.comma="addUser(filter, $event)"
                          type="text"
                          placeholder="Type user name and press Enter or comma"
                          class="flex-1 min-w-[120px] border-none outline-none bg-transparent text-sm" />
                      </div>
                    </div>
                    <!-- Regular select for dropdown fields -->
                    <select v-else-if="isSelectField(filter.field)" 
                      v-model="filter.value" 
                      @change="updateDynamicFilter(index)"
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                      <option value="">Select...</option>
                      <option v-for="option in getFieldOptions(filter.field)" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </option>
                    </select>
                    <!-- Text input for other fields -->
                    <input v-else
                      v-model="filter.value"
                      @input="updateDynamicFilter(index)"
                      type="text"
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />
                  </div>

                  <!-- Remove Button -->
                  <button @click="removeDynamicFilter(index)"
                    class="p-1 text-gray-400 hover:text-red-600 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Bottom Actions -->
              <div v-if="dynamicFilters.length > 0" class="flex justify-between items-center pt-4 mt-4 border-t border-gray-200">
                <button @click="clearAllDynamicFilters"
                  class="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                  title="Clear all filters and search to show all issues">
                  Clear All
                </button>
                <button @click="applyFilters"
                  :class="[
                    'px-4 py-2 text-sm font-medium rounded transition-colors',
                    hasPendingChanges 
                      ? 'bg-gray-900 text-white hover:bg-gray-800' 
                      : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                  ]"
                  :disabled="!hasPendingChanges">
                  <span v-if="hasPendingChanges">Apply Filters</span>
                  <span v-else>Filters Applied</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Backdrop -->
      <div class="fixed inset-0 z-40" @click="showFilterPanel = false"></div>
    </div>
  </div>
</template>

<script setup>
import { Select } from "frappe-ui"
import { computed, ref, watch, onMounted, onUnmounted } from "vue"
import CustomSearchBox from "./CustomSearchBox.vue"
import { getTagColor } from "../data/issues"

// Props
const props = defineProps({
  searchQuery: {
    type: String,
    default: "",
  },
  filters: {
    type: Object,
    default: () => ({
      status: "",
      priority: "",
      assignee: "",
      tags: "",
      sortBy: "creation",
    }),
  },
  statusOptions: {
    type: Array,
    default: () => [],
  },
  priorityOptions: {
    type: Array,
    default: () => [],
  },
  assigneeOptions: {
    type: Array,
    default: () => [],
  },
  tagsOptions: {
    type: Array,
    default: () => [],
  },
  filteredCount: {
    type: Number,
    default: 0,
  },
  issues: {
    type: Array,
    default: () => [],
  },
})

// Emits
const emit = defineEmits(["update:searchQuery", "update:filters", "suggestion-selected"])

// Local reactive state
const localSearchQuery = ref(props.searchQuery)
const localFilters = ref({ ...props.filters })
const searchBoxRef = ref(null)

// Dynamic filter system state
const showFilterPanel = ref(false)
const dynamicFilters = ref([]) // Pending/draft filters (not applied yet)
const appliedFilters = ref([]) // Currently applied filters
let filterIdCounter = 0

// Multi-select state for users
const userInputValue = ref({})

// Track if there are pending changes
const hasPendingChanges = computed(() => {
  return JSON.stringify(dynamicFilters.value) !== JSON.stringify(appliedFilters.value)
})

// localStorage keys
const STORAGE_KEYS = {
  SEARCH_QUERY: 'issue_filters_search_query',
  DYNAMIC_FILTERS: 'issue_filters_dynamic_filters',
  SHOW_FILTER_PANEL: 'issue_filters_show_panel'
}

// Get available tags from issues
const availableTags = computed(() => {
  const tagSet = new Set()
  props.issues.forEach(issue => {
    if (issue._user_tags && Array.isArray(issue._user_tags)) {
      issue._user_tags.forEach(tag => {
        if (tag && tag.trim()) {
          tagSet.add(tag.trim())
        }
      })
    }
  })
  
  return Array.from(tagSet).sort().map(tag => ({
    label: tag,
    value: tag,
    color: getTagColor(tag)
  }))
})

// Available fields for filtering based on Issue doctype schema
const availableFields = computed(() => [
  // Core Issue Fields
  {
    value: 'subject',
    label: 'Subject',
    description: 'Filter by issue title',
    icon: 'type',
    type: 'text'
  },
  {
    value: 'status',
    label: 'Status',
    description: 'Filter by issue status (New, In Review, etc.)',
    icon: 'circle',
    type: 'select'
  },
  {
    value: 'raised_by',
    label: 'Raised By (Email)',
    description: 'Filter by who raised the issue',
    icon: 'user',
    type: 'text'
  },
  {
    value: 'description',
    label: 'Description',
    description: 'Filter by issue description',
    icon: 'file-text',
    type: 'text'
  },
  
  // Customer & Contact Fields
  {
    value: 'customer',
    label: 'Customer',
    description: 'Filter by customer',
    icon: 'building',
    type: 'link'
  },
  {
    value: 'contact',
    label: 'Contact',
    description: 'Filter by contact person',
    icon: 'user',
    type: 'link'
  },
  {
    value: 'lead',
    label: 'Lead',
    description: 'Filter by associated lead',
    icon: 'user-plus',
    type: 'link'
  },

  
  // Custom Fields
  {
    value: 'custom_assigned_csm_team',
    label: 'Assigned CSM Team',
    description: 'Filter by assigned CSM team',
    icon: 'users',
    type: 'select'
  },
  {
    value: 'custom_users_assigned',
    label: 'Users Assigned',
    description: 'Filter by assigned users',
    icon: 'user-check',
    type: 'multiselect'
  },
  
  // Date Fields
  {
    value: 'creation',
    label: 'Created Date',
    description: 'Filter by creation date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)',
    icon: 'calendar',
    type: 'datetime'
  },
  {
    value: 'modified',
    label: 'Modified Date', 
    description: 'Filter by last modified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)',
    icon: 'clock',
    type: 'datetime'
  },
  // Tags (User Tags)
  {
    value: '_user_tags',
    label: 'Tags',
    description: 'Filter by user tags',
    icon: 'tag',
    type: 'tags'
  }
])

// Sort options (static)
const sortOptions = computed(() => [
  { label: "Created Date (Newest)", value: "creation desc" },
  { label: "Created Date (Oldest)", value: "creation asc" },
  { label: "Modified Date (Newest)", value: "modified desc" },
  { label: "Modified Date (Oldest)", value: "modified asc" },
  { label: "Subject (A-Z)", value: "subject asc" },
  { label: "Subject (Z-A)", value: "subject desc" },
  { label: "Priority", value: "priority asc" },
  { label: "Status", value: "status asc" },
])

// Watch for prop changes and update local state
watch(
  () => props.searchQuery,
  (newValue) => {
    localSearchQuery.value = newValue
  },
)

watch(
  () => props.filters,
  (newValue) => {
    localFilters.value = { ...newValue }
  },
  { deep: true },
)

// Keyboard shortcut handler
const handleKeyboardShortcut = (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
    event.preventDefault()
    focusSearch()
  }
}

// Focus search function
const focusSearch = () => {
  if (searchBoxRef.value) {
    searchBoxRef.value.focus()
    searchBoxRef.value.select()
  }
}

// Event handlers
const handleSearchChange = (value) => {
  localSearchQuery.value = value
  emit("update:searchQuery", value)
  // Search changes apply immediately (not part of filter system)
}

const handleSuggestionSelected = (suggestion) => {
  emit("suggestion-selected", suggestion)
}

const handleFilterChange = () => {
  emit("update:filters", { ...localFilters.value })
}

// Modern filter features
const activeFilterCount = computed(() => {
  let count = 0
  if (localFilters.value.status) count++
  if (localFilters.value.priority) count++
  if (localFilters.value.assignee) count++
  if (localFilters.value.tags) count++
  if (localFilters.value.sortBy !== 'creation desc') count++
  return count
})

const activeFilters = computed(() => {
  const filters = []
  
  if (localFilters.value.status) {
    const statusOption = props.statusOptions.find(opt => opt.value === localFilters.value.status)
    filters.push({
      key: 'status',
      label: 'Status',
      value: statusOption?.label || localFilters.value.status,
      colorClass: 'bg-green-100 text-green-800 border-green-200'
    })
  }
  
  if (localFilters.value.priority) {
    const priorityOption = props.priorityOptions.find(opt => opt.value === localFilters.value.priority)
    filters.push({
      key: 'priority',
      label: 'Priority',
      value: priorityOption?.label || localFilters.value.priority,
      colorClass: 'bg-orange-100 text-orange-800 border-orange-200'
    })
  }
  
  if (localFilters.value.assignee) {
    const assigneeOption = props.assigneeOptions.find(opt => opt.value === localFilters.value.assignee)
    filters.push({
      key: 'assignee',
      label: 'Assignee',
      value: assigneeOption?.label || localFilters.value.assignee,
      colorClass: 'bg-blue-100 text-blue-800 border-blue-200'
    })
  }
  
  if (localFilters.value.tags) {
    const tagOption = props.tagsOptions.find(opt => opt.value === localFilters.value.tags)
    filters.push({
      key: 'tags',
      label: 'Tags',
      value: tagOption?.label || localFilters.value.tags,
      colorClass: 'bg-purple-100 text-purple-800 border-purple-200'
    })
  }
  
  if (localFilters.value.sortBy !== 'creation desc') {
    const sortOption = sortOptions.value.find(opt => opt.value === localFilters.value.sortBy)
    filters.push({
      key: 'sortBy',
      label: 'Sort',
      value: sortOption?.label || localFilters.value.sortBy,
      colorClass: 'bg-indigo-100 text-indigo-800 border-indigo-200'
    })
  }
  
  return filters
})

const clearFilter = (filterKey) => {
  if (filterKey === 'sortBy') {
    localFilters.value[filterKey] = 'creation desc'
  } else {
    localFilters.value[filterKey] = ''
  }
  handleFilterChange()
}

const clearAllFilters = () => {
  localFilters.value = {
    status: '',
    priority: '',
    assignee: '',
    tags: '',
    sortBy: 'creation desc'
  }
  handleFilterChange()
}

// Dynamic filter functions
const addNewFilter = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  if (!field) return

  const newFilter = {
    id: ++filterIdCounter,
    field: fieldValue,
    operator: getDefaultOperator(fieldValue),
    value: '',
    type: field.type
  }

  dynamicFilters.value.push(newFilter)
  
  // Initialize user input value for multiselect fields
  if (fieldValue === 'custom_users_assigned') {
    userInputValue.value[newFilter.id] = ''
  }
  
  // Keep dialog open - don't close it when adding new filter
  // User should be able to add multiple filters before applying
}

const removeDynamicFilter = (index) => {
  dynamicFilters.value.splice(index, 1)
  // Don't auto-apply - user needs to click Apply Filters
}

const clearAllDynamicFilters = () => {
  // Reset all filter states
  dynamicFilters.value = []
  appliedFilters.value = []
  userInputValue.value = {}
  
  // Reset search query to empty
  localSearchQuery.value = ''
  
  // Clear the search box UI as well
  if (searchBoxRef.value) {
    searchBoxRef.value.clearSearch?.()
  }
  
  // Reset local filters to default values
  localFilters.value = {
    status: '',
    priority: '',
    assignee: '',
    tags: '',
    sortBy: 'creation desc'
  }
  
  // Clear localStorage
  localStorage.removeItem(STORAGE_KEYS.DYNAMIC_FILTERS)
  localStorage.removeItem(STORAGE_KEYS.SEARCH_QUERY)
  localStorage.removeItem(STORAGE_KEYS.SHOW_FILTER_PANEL)
  
  // Emit changes to parent to reset issue table to default state
  emit("update:searchQuery", '')
  emit("update:filters", { ...localFilters.value })
  
  // Update the applied filters (which will be empty, showing all issues)
  updateDynamicFiltersOutput()
  
  // Close filter panel if open
  showFilterPanel.value = false
}

const updateDynamicFilter = (index) => {
  // Trigger reactivity and update parent
  updateDynamicFiltersOutput()
  saveFiltersToStorage()
}

const updateDynamicFiltersOutput = () => {
  // Convert applied filters (not pending ones) to the format expected by parent component
  const filterObj = {}
  
  appliedFilters.value.forEach(filter => {
    if (filter.value) {
      const key = filter.field === 'issue_type' ? 'tags' : 
                  filter.field === 'raised_by' ? 'assignee' : filter.field
      
      if (filter.operator === 'equals') {
        filterObj[key] = filter.value
      } else if (filter.operator === 'contains') {
        filterObj[key] = filter.value
      } else if (filter.operator === 'not_equals') {
        filterObj[key] = `!${filter.value}`
      } else if (filter.operator === 'in') {
        filterObj[key] = filter.value
      }
      // Add more operator handling as needed
    }
  })
  
  // Update local filters and emit
  localFilters.value = { ...localFilters.value, ...filterObj }
  emit("update:filters", { ...localFilters.value })
}

// Helper functions for dynamic filters
const getFieldLabel = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  return field?.label || fieldValue
}

const getDefaultOperator = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  if (field?.type === 'select') return 'equals'
  if (field?.type === 'text') return 'like'
  if (field?.type === 'date' || field?.type === 'datetime') return 'equals'
  if (field?.type === 'time') return 'equals'
  if (field?.type === 'duration') return 'equals'
  if (field?.type === 'boolean') return 'equals'
  if (field?.type === 'link') return 'equals'
  if (field?.type === 'multiselect' || field?.type === 'tags') return 'like'
  return 'equals'
}

const getOperatorOptions = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  
  if (field?.type === 'select') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'In', value: 'in' },
      { label: 'Not In', value: 'not_in' }
    ]
  }
  
  if (field?.type === 'text') {
    return [
      { label: 'Like', value: 'like' },
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'Starts with', value: 'starts_with' },
      { label: 'Ends with', value: 'ends_with' },
      { label: 'Is Set', value: 'is_set' },
      { label: 'Is Not Set', value: 'is_not_set' }
    ]
  }
  
  if (field?.type === 'date' || field?.type === 'datetime') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'Greater than', value: 'greater_than' },
      { label: 'Less than', value: 'less_than' },
      { label: 'Greater than or equal', value: 'greater_than_equal' },
      { label: 'Less than or equal', value: 'less_than_equal' },
      { label: 'Between', value: 'between' },
      { label: 'Is Set', value: 'is_set' },
      { label: 'Is Not Set', value: 'is_not_set' }
    ]
  }
  
  if (field?.type === 'time') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'Greater than', value: 'greater_than' },
      { label: 'Less than', value: 'less_than' }
    ]
  }
  
  if (field?.type === 'duration') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'Greater than', value: 'greater_than' },
      { label: 'Less than', value: 'less_than' },
      { label: 'Is Set', value: 'is_set' },
      { label: 'Is Not Set', value: 'is_not_set' }
    ]
  }
  
  if (field?.type === 'boolean') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' }
    ]
  }
  
  if (field?.type === 'link') {
    return [
      { label: 'Equals', value: 'equals' },
      { label: 'Not Equals', value: 'not_equals' },
      { label: 'Like', value: 'like' },
      { label: 'In', value: 'in' },
      { label: 'Not In', value: 'not_in' },
      { label: 'Is Set', value: 'is_set' },
      { label: 'Is Not Set', value: 'is_not_set' }
    ]
  }
  
  if (field?.type === 'multiselect' || field?.type === 'tags') {
    return [
      { label: 'Like', value: 'like' },
      { label: 'Not Like', value: 'not_like' },
      { label: 'In', value: 'in' },
      { label: 'Not In', value: 'not_in' },
      { label: 'Is Set', value: 'is_set' },
      { label: 'Is Not Set', value: 'is_not_set' }
    ]
  }
  
  return [{ label: 'Equals', value: 'equals' }]
}

const isSelectField = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  return field?.type === 'select' || field?.type === 'tags'
}

const isDateField = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  return field?.type === 'date'
}

const isDateTimeField = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  return field?.type === 'datetime'
}

const getFieldOptions = (fieldValue) => {
  switch (fieldValue) {
    case 'status':
      return props.statusOptions
    case 'priority':
      return props.priorityOptions
    case 'raised_by':
      return props.assigneeOptions
    case 'issue_type':
      return props.tagsOptions
    case '_user_tags':
      return availableTags.value
    case 'custom_assigned_csm_team':
      // Mock CSM teams - in real implementation, this should come from props or API
      return [
        { label: 'Team Alpha', value: 'team-alpha' },
        { label: 'Team Beta', value: 'team-beta' },
        { label: 'Team Gamma', value: 'team-gamma' },
        { label: 'Team Delta', value: 'team-delta' }
      ]
    case 'custom_users_assigned':
      // Mock users - in real implementation, this should come from props or API
      return [
        { label: 'John Doe', value: 'john.doe' },
        { label: 'Jane Smith', value: 'jane.smith' },
        { label: 'Bob Wilson', value: 'bob.wilson' },
        { label: 'Alice Johnson', value: 'alice.johnson' }
      ]
    default:
      return []
  }
}

const getFieldPlaceholder = (fieldValue) => {
  const field = availableFields.value.find(f => f.value === fieldValue)
  
  switch (fieldValue) {
    // Text fields
    case 'subject':
      return 'Enter issue title...'
    case 'description':
      return 'Enter description text...'
    case 'raised_by':
      return 'Enter email address...'
    case 'customer_name':
      return 'Enter customer name...'
    case 'naming_series':
      return 'Enter series (e.g., ISS-2025-)...'
    
    // Date fields
    case 'creation':
    case 'modified':
    case 'opening_date':
    case 'sla_resolution_date':
    case 'first_responded_on':
      return 'YYYY-MM-DD or YYYY-MM-DD HH:MM:SS'
    case 'response_by':
    case 'sla_resolution_by':
      return 'YYYY-MM-DD HH:MM:SS'
    
    // Time fields
    case 'opening_time':
      return 'HH:MM:SS'
    
    // Duration fields
    case 'first_response_time':
    case 'avg_response_time':
    case 'resolution_time':
    case 'user_resolution_time':
    case 'total_hold_time':
      return 'Enter duration (e.g., 2:30:00 for 2h 30m)'
    
    // Link fields
    case 'customer':
      return 'Enter customer name or ID...'
    case 'contact':
      return 'Enter contact name or ID...'
    case 'lead':
      return 'Enter lead name or ID...'
    case 'project':
      return 'Enter project name or ID...'
    case 'company':
      return 'Enter company name or ID...'
    case 'service_level_agreement':
      return 'Enter SLA name or ID...'
    case 'custom_assigned_csm_team':
      return 'Enter team name or ID...'
    case 'email_account':
      return 'Enter email account name...'
    case 'issue_split_from':
      return 'Enter parent issue ID...'
    
    // Boolean fields
    case 'via_customer_portal':
      return 'Enter 1 for Yes, 0 for No'
    
    // Multiselect/Tags fields
    case 'custom_users_assigned':
      return 'Enter user names (comma separated)...'
    case 'custom_labels':
      return 'Enter labels (comma separated)...'
    case '_user_tags':
      return 'Enter tags (comma separated)...'
    
    default:
      // Generate placeholder based on field type
      if (field?.type === 'date' || field?.type === 'datetime') {
        return 'YYYY-MM-DD or YYYY-MM-DD HH:MM:SS'
      } else if (field?.type === 'time') {
        return 'HH:MM:SS'
      } else if (field?.type === 'duration') {
        return 'Enter duration (e.g., 2:30:00)'
      } else if (field?.type === 'boolean') {
        return 'Enter 1 for Yes, 0 for No'
      } else if (field?.type === 'link') {
        return `Enter ${field?.label?.toLowerCase() || 'value'} name or ID...`
      } else if (field?.type === 'multiselect' || field?.type === 'tags') {
        return `Enter ${field?.label?.toLowerCase() || 'values'} (comma separated)...`
      } else {
        return `Enter ${field?.label?.toLowerCase() || 'value'}...`
      }
  }
}

// Tag styling function (same as in IssueTable for consistency)
const getTagStyle = (tag) => {
  // Get tag color from API
  const hexColor = getTagColor(tag)

  if (hexColor) {
    // Convert hex color to RGB for background and text colors
    const hex = hexColor.replace('#', '')
    const r = parseInt(hex.substr(0, 2), 16)
    const g = parseInt(hex.substr(2, 2), 16)
    const b = parseInt(hex.substr(4, 2), 16)

    // Create background color (lighter version with opacity)
    const bgColor = `rgba(${r}, ${g}, ${b}, 0.1)`

    // Create text color (darker version for contrast)
    const textColor = `rgb(${Math.max(r - 50, 0)}, ${Math.max(g - 50, 0)}, ${Math.max(b - 50, 0)})`

    return {
      backgroundColor: bgColor,
      color: textColor,
      borderColor: textColor
    }
  }

  // Fallback to default styling
  return {
    backgroundColor: '#f3f4f6',
    color: '#374151',
    borderColor: '#d1d5db'
  }
}

// Multi-select user functions
const getSelectedUsers = (value) => {
  if (!value) return []
  return value.split(',').map(user => user.trim()).filter(user => user)
}

const addUser = (filter, event) => {
  event.preventDefault()
  const inputValue = userInputValue.value[filter.id]?.trim()
  if (!inputValue) return
  
  const currentUsers = getSelectedUsers(filter.value)
  if (!currentUsers.includes(inputValue)) {
    const newUsers = [...currentUsers, inputValue].join(', ')
    filter.value = newUsers
    // Don't auto-apply - user needs to click Apply
  }
  
  userInputValue.value[filter.id] = ''
}

const removeUser = (filter, userToRemove) => {
  const currentUsers = getSelectedUsers(filter.value)
  const newUsers = currentUsers.filter(user => user !== userToRemove).join(', ')
  filter.value = newUsers
  // Don't auto-apply - user needs to click Apply
}

// localStorage functions
const saveFiltersToStorage = () => {
  localStorage.setItem(STORAGE_KEYS.SEARCH_QUERY, localSearchQuery.value)
  // Save both pending and applied filters
  const filterState = {
    pending: dynamicFilters.value,
    applied: appliedFilters.value
  }
  localStorage.setItem(STORAGE_KEYS.DYNAMIC_FILTERS, JSON.stringify(filterState))
  localStorage.setItem(STORAGE_KEYS.SHOW_FILTER_PANEL, showFilterPanel.value.toString())
}

const loadFiltersFromStorage = () => {
  // Load search query
  const savedSearchQuery = localStorage.getItem(STORAGE_KEYS.SEARCH_QUERY)
  if (savedSearchQuery) {
    localSearchQuery.value = savedSearchQuery
    emit("update:searchQuery", savedSearchQuery)
  }
  
  // Load dynamic filters
  const savedFilters = localStorage.getItem(STORAGE_KEYS.DYNAMIC_FILTERS)
  if (savedFilters) {
    try {
      const filterState = JSON.parse(savedFilters)
      // Handle both old format (array) and new format (object with pending/applied)
      if (Array.isArray(filterState)) {
        // Old format - treat as applied filters
        appliedFilters.value = filterState
        dynamicFilters.value = [...filterState] // Copy to pending
      } else {
        // New format
        dynamicFilters.value = filterState.pending || []
        appliedFilters.value = filterState.applied || []
      }
      updateDynamicFiltersOutput()
    } catch (e) {
      console.warn('Failed to parse saved filters:', e)
    }
  }
  
  // Load panel state
  const savedPanelState = localStorage.getItem(STORAGE_KEYS.SHOW_FILTER_PANEL)
  if (savedPanelState !== null) {
    showFilterPanel.value = savedPanelState === 'true'
  }
}

// Function to remove applied filter and immediately apply the change
const removeAppliedFilter = (index) => {
  // Get the filter before removing it
  const removedFilter = appliedFilters.value[index]
  
  // Remove from applied filters
  appliedFilters.value.splice(index, 1)
  
  // Also remove from pending filters if it exists there
  if (removedFilter) {
    const pendingIndex = dynamicFilters.value.findIndex(f => f.id === removedFilter.id)
    if (pendingIndex !== -1) {
      dynamicFilters.value.splice(pendingIndex, 1)
    }
  }
  
  // Immediately apply the change (update issue table)
  updateDynamicFiltersOutput()
  
  // Save to localStorage
  saveFiltersToStorage()
}

// Apply filters function - this is the only place where filters actually get applied
const applyFilters = () => {
  if (!hasPendingChanges.value) return
  
  // Copy pending filters to applied filters
  appliedFilters.value = JSON.parse(JSON.stringify(dynamicFilters.value))
  
  // Apply the filters to parent component
  updateDynamicFiltersOutput()
  
  // Save to storage
  saveFiltersToStorage()
  
  // Close panel
  showFilterPanel.value = false
}

// Only save search query changes automatically, not filter changes
watch(localSearchQuery, () => {
  localStorage.setItem(STORAGE_KEYS.SEARCH_QUERY, localSearchQuery.value)
})

// Lifecycle hooks for keyboard shortcuts and localStorage
onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcut)
  loadFiltersFromStorage()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcut)
  saveFiltersToStorage()
})
</script>

<style scoped>
.awesome-search {
  transition: all 0.3s ease;
}

.awesome-search:deep(.search-box) {
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border: 2px solid #e5e7eb;
  background: white;
  transition: all 0.3s ease;
}

.awesome-search:deep(.search-box):hover {
  border-color: #3b82f6;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.awesome-search:deep(.search-box):focus-within {
  border-color: #3b82f6;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.awesome-search:deep(.search-input) {
  border: none;
  outline: none;
  background: transparent;
  font-size: 16px;
  padding: 16px 16px 16px 44px;
  height: auto;
  border-radius: 12px;
}

.awesome-search:deep(.search-input)::placeholder {
  color: #9ca3af;
  font-weight: 400;
}

.awesome-search:deep(.search-icon) {
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
}

/* Keyboard shortcut styling */
kbd {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
}

/* Modern Filter Styling */
.modern-filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.modern-filter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #4b5563;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

/* Modern Select Styling */
.modern-select:deep(.form-select) {
  border: 1.5px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  min-height: 42px;
}

.modern-select:deep(.form-select):hover {
  border-color: #d1d5db;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.modern-select:deep(.form-select):focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  transform: translateY(-1px);
  outline: none;
}

/* Filter-specific styling */
.status-select:deep(.form-select):focus {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.priority-select:deep(.form-select):focus {
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

.assignee-select:deep(.form-select):focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.tags-select:deep(.form-select):focus {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.sort-select:deep(.form-select):focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

/* Active Filter Indicator */
.filter-active-indicator {
  position: absolute;
  top: -0.25rem;
  right: -0.25rem;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  border: 2px solid white;
  animation: pulse-indicator 2s infinite;
  z-index: 10;
}

@keyframes pulse-indicator {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

/* Modern Filter Pills */
.modern-filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);
}

.modern-filter-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.modern-filter-pill button {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  padding: 0.125rem;
  transition: all 0.2s ease;
}

.modern-filter-pill button:hover {
  transform: scale(1.1);
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .modern-select:deep(.form-select) {
    font-size: 0.875rem;
    padding: 0.625rem 0.875rem;
    min-height: 38px;
  }
  
  .modern-filter-label {
    font-size: 0.6875rem;
  }
}

/* Enhanced hover states */
.modern-filter-group:hover .modern-filter-label {
  color: #374151;
}

/* Smooth transitions for all elements */
.modern-filter-group * {
  transition: all 0.2s ease;
}
</style>