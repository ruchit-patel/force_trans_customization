<template>
  <div class="bg-white p-6 rounded-lg shadow-sm border mb-6">
    <!-- Search Section -->
    <div class="mb-6">
      <div class="relative max-w-2xl mx-auto">
        <CustomSearchBox ref="searchBoxRef" :model-value="searchQuery" @update:model-value="handleSearchChange"
          @suggestion-selected="handleSuggestionSelected" :issues="issues"
          placeholder="Search issues by title, description, assignee..." class="awesome-search" />
        <div v-if="searchQuery" class="absolute top-full left-0 right-0 mt-1 text-sm text-gray-500 text-center">
          Searching in {{ filteredCount }} issues
        </div>
      </div>
    </div>

    <!-- Filter Controls -->
    <div class="border-t border-gray-200 pt-4">
      <div class="flex items-center justify-between">
        <!-- Left: Filter button and active filters -->
        <div class="flex items-center space-x-3 flex-1">
          <button @click="showFilterPanel = !showFilterPanel"
            class="inline-flex items-center space-x-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium text-gray-700 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.414A1 1 0 013 6.707V4z"/>
            </svg>
            <span>Filters</span>
            <span v-if="appliedFilters.length > 0" class="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
              {{ appliedFilters.length }}
            </span>
          </button>

          <!-- Active Filters Display -->
          <div v-if="appliedFilters.length > 0" class="flex items-center flex-1 overflow-x-auto flex-wrap gap-2">
            <div v-for="(filter, index) in appliedFilters" :key="filter.id" 
              class="flex items-center space-x-1 bg-green-100 border border-green-200 rounded px-2 py-1 text-sm whitespace-nowrap">
              <span class="text-green-800 font-medium">{{ getFieldLabel(filter.field) }}</span>
              <span class="text-green-600">{{ filter.operator }}</span>
              <span class="text-green-900">{{ getDisplayValue(filter) }}</span>
              <button @click="removeAppliedFilter(index)" class="text-green-400 hover:text-red-600 ml-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Right: Clear and Apply buttons -->
        <div class="flex items-center space-x-2 ml-4">
          <button v-if="appliedFilters.length > 0 || searchQuery" 
            @click="clearAllFilters"
            class="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
            Clear All
          </button>
          <button v-if="pendingFilters.length > 0"
            @click="applyFilters"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-md transition-colors',
              hasPendingChanges ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-600 cursor-not-allowed'
            ]"
            :disabled="!hasPendingChanges">
            {{ hasPendingChanges ? 'Apply Filters' : 'Filters Applied' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Filter Panel -->
    <div v-if="showFilterPanel" class="relative">
      <div class="absolute top-2 left-0 right-0 z-50 bg-white border border-gray-200 rounded-lg shadow-lg" @click.stop>
        <div class="flex">
          <!-- Left: Field Selection -->
          <div class="w-48 border-r border-gray-200 bg-gray-50">
            <div class="p-3 border-b border-gray-200">
              <h4 class="text-sm font-medium text-gray-900">Add Filter</h4>
            </div>
            <div class="max-h-64 overflow-y-auto">
              <button v-for="field in availableFields" :key="field.value"
                @click.stop="addFilter(field.value)"
                class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center justify-between">
                <span>{{ field.label }}</span>
                <span class="text-xs text-gray-400 bg-gray-200 px-1 rounded">{{ field.type }}</span>
              </button>
            </div>
          </div>

          <!-- Right: Active Filters -->
          <div class="flex-1 min-w-96">
            <div class="p-4">
              <div v-if="pendingFilters.length === 0" class="text-center py-8 text-gray-500">
                <p class="text-sm">Select a field from the left to add a filter</p>
              </div>
              
              <div v-else class="space-y-4">
                <div v-for="(filter, index) in pendingFilters" :key="filter.id" 
                  class="flex items-start space-x-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  
                  <!-- Field Name -->
                  <div class="w-24 text-sm font-medium text-gray-700 pt-2">
                    {{ getFieldLabel(filter.field) }}
                  </div>

                  <!-- Operator -->
                  <div class="w-28">
                    <select v-model="filter.operator" 
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                      <option v-for="op in getOperatorsForField(filter.field)" :key="op.value" :value="op.value">
                        {{ op.label }}
                      </option>
                    </select>

                    
                  </div>

                  <!-- Dynamic Value Input -->
                  <div class="flex-1">
                    <!-- Text Input -->
                    <input v-if="getFieldType(filter.field) === 'text'" 
                      v-model="filter.value" 
                      type="text" 
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                    
                    <!-- Email Input -->
                    <input v-else-if="getFieldType(filter.field) === 'email'" 
                      v-model="filter.value" 
                      type="email" 
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                    
                    <!-- DateTime Input -->
                    <div v-else-if="getFieldType(filter.field) === 'datetime'" class="space-y-2">
                      <input v-model="filter.value" 
                        type="datetime-local" 
                        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                      <p class="text-xs text-gray-500">Select date and time</p>
                    </div>

                    <!-- Date Input -->
                    <input v-else-if="getFieldType(filter.field) === 'date'" 
                      v-model="filter.value" 
                      type="date" 
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                    
                    <!-- Select/ComboBox for Options -->
                    <div v-else-if="getFieldType(filter.field) === 'select'" class="relative">
                      <select v-if="!filter.isMultiSelect" 
                        v-model="filter.value" 
                        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        <option value="">Select {{ getFieldLabel(filter.field) }}...</option>
                        <option v-for="option in getFieldOptions(filter.field)" :key="option.value" :value="option.value">
                          {{ option.label }}
                        </option>
                      </select>
                      
                      <!-- Multi-select for tags, users, etc -->
                      <div v-else class="space-y-2">
                        <div class="flex flex-wrap gap-1 mb-2">
                          <span v-for="(selectedValue, idx) in getSelectedValues(filter.value)" :key="idx"
                            class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                            {{ selectedValue }}
                            <button @click="removeSelectedValue(filter, idx)" class="ml-1 text-blue-600 hover:text-red-600">
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                              </svg>
                            </button>
                          </span>
                        </div>
                        <select @change="addSelectedValue(filter, $event.target.value); $event.target.value = ''" 
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                          <option value="">Add {{ getFieldLabel(filter.field) }}...</option>
                          <option v-for="option in getAvailableOptions(filter)" :key="option.value" :value="option.value">
                            {{ option.label }}
                          </option>
                        </select>
                      </div>
                    </div>

                    <!-- Link/Reference Input with ComboBox -->
                    <div v-else-if="getFieldType(filter.field) === 'link'" class="relative">
                      <div class="relative">
                        <input v-model="filter.searchValue" 
                          @input="handleLinkSearch(filter, $event.target.value)"
                          @focus="filter.showSuggestions = true"
                          type="text" 
                          :placeholder="`Search and select ${getFieldLabel(filter.field)}...`"
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                        
                        <!-- Selected Value Display -->
                        <div v-if="filter.value && filter.displayValue" 
                          class="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm">
                          <div class="flex items-center justify-between">
                            <span class="text-green-800">Selected: {{ filter.displayValue }}</span>
                            <button @click="clearLinkValue(filter)" class="text-green-600 hover:text-red-600">
                              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                              </svg>
                            </button>
                          </div>
                        </div>

                        <!-- Suggestions Dropdown -->
                        <div v-if="filter.showSuggestions && filter.suggestions && filter.suggestions.length > 0" 
                          class="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-md shadow-lg z-10 max-h-48 overflow-y-auto">
                          <button v-for="suggestion in filter.suggestions" :key="suggestion.value"
                            @click="selectLinkValue(filter, suggestion)"
                            class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 border-b border-gray-100 last:border-b-0">
                            <div class="font-medium">{{ suggestion.label }}</div>
                            <div v-if="suggestion.subtitle" class="text-xs text-gray-500">{{ suggestion.subtitle }}</div>
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- Tags/Multi-value Input -->
                    <div v-else-if="getFieldType(filter.field) === 'tags'" class="space-y-2">
                      <div class="flex flex-wrap gap-1 mb-2">
                        <span v-for="(tag, idx) in getTags(filter.value)" :key="idx"
                          class="inline-flex items-center px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                          {{ tag }}
                          <button @click="removeTag(filter, idx)" class="ml-1 text-purple-600 hover:text-red-600">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                          </button>
                        </span>
                      </div>
                      <input v-model="filter.tagInput" 
                        @keyup.enter="addTag(filter)"
                        @keyup.comma="addTag(filter)"
                        type="text" 
                        placeholder="Type tags and press Enter (comma separated)"
                        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                      <p class="text-xs text-gray-500">Press Enter or comma to add tags</p>
                    </div>
                  </div>

                  <!-- Remove Button -->
                  <button @click="removeFilter(index)" class="p-1 text-gray-400 hover:text-red-600 mt-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Bottom Actions -->
              <div v-if="pendingFilters.length > 0" class="flex justify-between items-center pt-4 mt-4 border-t border-gray-200">
                <button @click="clearAllFilters" class="text-sm text-gray-600 hover:text-gray-900">
                  Clear All
                </button>
                <button @click="applyFilters" :disabled="!hasPendingChanges"
                  :class="[
                    'px-4 py-2 text-sm font-medium rounded',
                    hasPendingChanges ? 'bg-gray-900 text-white hover:bg-gray-800' : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                  ]">
                  {{ hasPendingChanges ? 'Apply Filters' : 'Filters Applied' }}
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

// Props
const props = defineProps({
  searchQuery: { type: String, default: "" },
  filters: { type: Object, default: () => ({}) },
  filteredCount: { type: Number, default: 0 },
  issues: { type: Array, default: () => [] },
})

// Emits
const emit = defineEmits(["update:searchQuery", "update:filters", "suggestion-selected"])

// State
const searchQuery = ref(props.searchQuery)
const showFilterPanel = ref(false)
const pendingFilters = ref([])
const appliedFilters = ref([])
let filterIdCounter = 0

// Enhanced Field Configuration with Types
const availableFields = [
  { value: 'subject', label: 'Subject', type: 'text' },
  { value: 'description', label: 'Description', type: 'text' },
  { value: 'status', label: 'Status', type: 'select' },
  { value: 'priority', label: 'Priority', type: 'select' },
  { value: 'issue_type', label: 'Issue Type', type: 'select' },
  { value: 'raised_by', label: 'Raised By', type: 'email' },
  { value: 'owner', label: 'Owner', type: 'link' },
  { value: 'customer', label: 'Customer', type: 'link' },
  { value: 'project', label: 'Project', type: 'link' },
  { value: 'creation', label: 'Created Date', type: 'datetime' },
  { value: 'modified', label: 'Modified Date', type: 'datetime' },
  { value: 'custom_users_assigned', label: 'Users Assigned', type: 'select', multiSelect: true },
  { value: 'custom_assigned_csm_team', label: 'CSM Team', type: 'select' },
  { value: '_user_tags', label: 'Tags', type: 'tags' },
]

// Field Options Data
const fieldOptions = {
  status: [
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'closed', label: 'Closed' },
    { value: 'cancelled', label: 'Cancelled' }
  ],
  priority: [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'urgent', label: 'Urgent' }
  ],
  issue_type: [
    { value: 'bug', label: 'Bug' },
    { value: 'feature', label: 'Feature Request' },
    { value: 'support', label: 'Support' },
    { value: 'question', label: 'Question' }
  ],
  custom_users_assigned: [
    { value: 'john.doe@company.com', label: 'John Doe' },
    { value: 'jane.smith@company.com', label: 'Jane Smith' },
    { value: 'bob.wilson@company.com', label: 'Bob Wilson' }
  ],
  custom_assigned_csm_team: [
    { value: 'team_a', label: 'Team A - Enterprise' },
    { value: 'team_b', label: 'Team B - SMB' },
    { value: 'team_c', label: 'Team C - Support' }
  ]
}

// Operator options based on field type
const operatorsByType = {
  text: [
    { value: 'like', label: 'Contains' },
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'starts_with', label: 'Starts With' },
    { value: 'ends_with', label: 'Ends With' }
  ],
  email: [
    { value: 'equals', label: 'Equals' },
    { value: 'like', label: 'Contains' },
    { value: 'not_equals', label: 'Not Equals' }
  ],
  select: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'in', label: 'In' },
    { value: 'not_in', label: 'Not In' }
  ],
  link: [
    { value: 'equals', label: 'Is' },
    { value: 'not_equals', label: 'Is Not' },
    { value: 'like', label: 'Contains' }
  ],
  datetime: [
    { value: 'equals', label: 'On' },
    { value: 'greater_than', label: 'After' },
    { value: 'less_than', label: 'Before' },
    { value: 'between', label: 'Between' }
  ],
  date: [
    { value: 'equals', label: 'On' },
    { value: 'greater_than', label: 'After' },
    { value: 'less_than', label: 'Before' },
    { value: 'between', label: 'Between' }
  ],
  tags: [
    { value: 'has', label: 'Has Tag' },
    { value: 'has_all', label: 'Has All Tags' },
    { value: 'has_any', label: 'Has Any Tag' },
    { value: 'not_has', label: 'Does Not Have' }
  ]
}

// Computed
const hasPendingChanges = computed(() => {
  return JSON.stringify(pendingFilters.value) !== JSON.stringify(appliedFilters.value)
})

// Helper Functions
const getFieldType = (fieldValue) => {
  const field = availableFields.find(f => f.value === fieldValue)
  return field?.type || 'text'
}

const getFieldLabel = (fieldValue) => {
  const field = availableFields.find(f => f.value === fieldValue)
  return field?.label || fieldValue
}

const getFieldPlaceholder = (fieldValue) => {
  const placeholders = {
    subject: 'Enter issue title...',
    description: 'Enter description...',
    raised_by: 'Enter email address...',
    owner: 'Search for owner...',
    customer: 'Search for customer...',
    project: 'Search for project...',
    creation: 'Select date and time',
    modified: 'Select date and time'
  }
  return placeholders[fieldValue] || `Enter ${getFieldLabel(fieldValue).toLowerCase()}...`
}

const getOperatorsForField = (fieldValue) => {
  const fieldType = getFieldType(fieldValue)
  return operatorsByType[fieldType] || operatorsByType.text
}

const getFieldOptions = (fieldValue) => {
  return fieldOptions[fieldValue] || []
}

const getDisplayValue = (filter) => {
  if (filter.displayValue) return filter.displayValue
  if (Array.isArray(filter.value)) return filter.value.join(', ')
  return filter.value
}

// Multi-select and Tags Helpers
const getSelectedValues = (value) => {
  if (!value) return []
  return typeof value === 'string' ? value.split(',').map(v => v.trim()).filter(Boolean) : value
}

const removeSelectedValue = (filter, index) => {
  const values = getSelectedValues(filter.value)
  values.splice(index, 1)
  filter.value = values.join(', ')
}

const addSelectedValue = (filter, newValue) => {
  if (!newValue) return
  const values = getSelectedValues(filter.value)
  if (!values.includes(newValue)) {
    values.push(newValue)
    filter.value = values.join(', ')
  }
}

const getAvailableOptions = (filter) => {
  const allOptions = getFieldOptions(filter.field)
  const selectedValues = getSelectedValues(filter.value)
  return allOptions.filter(option => !selectedValues.includes(option.value))
}

// Tags Helpers
const getTags = (value) => {
  if (!value) return []
  return value.split(',').map(v => v.trim()).filter(Boolean)
}

const removeTag = (filter, index) => {
  const tags = getTags(filter.value)
  tags.splice(index, 1)
  filter.value = tags.join(', ')
}

const addTag = (filter) => {
  if (!filter.tagInput || !filter.tagInput.trim()) return
  
  const newTag = filter.tagInput.replace(',', '').trim()
  const currentTags = getTags(filter.value)
  
  if (newTag && !currentTags.includes(newTag)) {
    currentTags.push(newTag)
    filter.value = currentTags.join(', ')
  }
  
  filter.tagInput = ''
}

// Link/Reference Helpers
const handleLinkSearch = (filter, searchValue) => {
  filter.searchValue = searchValue
  
  // Mock search suggestions - replace with actual API call
  if (searchValue.length > 1) {
    // Simulate different data based on field type
    if (filter.field === 'customer') {
      filter.suggestions = [
        { value: 'cust_123', label: 'Acme Corporation', subtitle: 'Enterprise Customer' },
        { value: 'cust_456', label: 'Tech Solutions Inc', subtitle: 'SMB Customer' },
        { value: 'cust_789', label: 'Global Industries', subtitle: 'Enterprise Customer' }
      ].filter(item => item.label.toLowerCase().includes(searchValue.toLowerCase()))
    } else if (filter.field === 'project') {
      filter.suggestions = [
        { value: 'proj_123', label: 'Website Redesign', subtitle: 'Active Project' },
        { value: 'proj_456', label: 'Mobile App', subtitle: 'In Progress' },
        { value: 'proj_789', label: 'API Integration', subtitle: 'Planning' }
      ].filter(item => item.label.toLowerCase().includes(searchValue.toLowerCase()))
    } else if (filter.field === 'owner') {
      filter.suggestions = [
        { value: 'user_123', label: 'John Doe', subtitle: 'john.doe@company.com' },
        { value: 'user_456', label: 'Jane Smith', subtitle: 'jane.smith@company.com' },
        { value: 'user_789', label: 'Bob Wilson', subtitle: 'bob.wilson@company.com' }
      ].filter(item => item.label.toLowerCase().includes(searchValue.toLowerCase()))
    }
  } else {
    filter.suggestions = []
  }
}

const selectLinkValue = (filter, suggestion) => {
  filter.value = suggestion.value
  filter.displayValue = suggestion.label
  filter.searchValue = suggestion.label
  filter.showSuggestions = false
  filter.suggestions = []
}

const clearLinkValue = (filter) => {
  filter.value = ''
  filter.displayValue = ''
  filter.searchValue = ''
  filter.suggestions = []
}

// Main Functions
const addFilter = (fieldValue) => {
  const fieldConfig = availableFields.find(f => f.value === fieldValue)
  const newFilter = {
    id: ++filterIdCounter,
    field: fieldValue,
    operator: getOperatorsForField(fieldValue)[0]?.value || 'equals',
    value: '',
    isMultiSelect: fieldConfig?.multiSelect || false,
    // Link-specific properties
    searchValue: '',
    displayValue: '',
    suggestions: [],
    showSuggestions: false,
    // Tags-specific properties
    tagInput: ''
  }
  pendingFilters.value.push(newFilter)
}

const removeFilter = (index) => {
  pendingFilters.value.splice(index, 1)
}

const removeAppliedFilter = (index) => {
  appliedFilters.value.splice(index, 1)
  emitFilters()
}

const applyFilters = () => {
  if (!hasPendingChanges.value) return
  
  appliedFilters.value = JSON.parse(JSON.stringify(pendingFilters.value))
  emitFilters()
  showFilterPanel.value = false
}

const clearAllFilters = () => {
  pendingFilters.value = []
  appliedFilters.value = []
  searchQuery.value = ''
  
  emit("update:searchQuery", '')
  emit("update:filters", [])
  
  showFilterPanel.value = false
}

const emitFilters = () => {
  const filterData = appliedFilters.value
    .filter(f => f.value && f.value.toString().trim())
    .map(filter => ({
      field: filter.field,
      operator: filter.operator,
      value: filter.value.toString().trim(),
      displayValue: filter.displayValue || null
    }))
  
  emit("update:filters", filterData)
}

// Event handlers
const handleSearchChange = (value) => {
  searchQuery.value = value
  emit("update:searchQuery", value)
}

const handleSuggestionSelected = (suggestion) => {
  emit("suggestion-selected", suggestion)
}

// Watch props
watch(() => props.searchQuery, (newValue) => {
  searchQuery.value = newValue
})

// Load from localStorage on mount
onMounted(() => {
  const savedFilters = localStorage.getItem('issue_filters')
  if (savedFilters) {
    try {
      const parsed = JSON.parse(savedFilters)
      appliedFilters.value = parsed.applied || []
      pendingFilters.value = parsed.pending || []
    } catch (e) {
      console.warn('Failed to parse saved filters:', e)
    }
  }
})

// Save to localStorage when filters change
watch([appliedFilters, pendingFilters], () => {
  localStorage.setItem('issue_filters', JSON.stringify({
    applied: appliedFilters.value,
    pending: pendingFilters.value
  }))
}, { deep: true })
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

/* Custom scrollbar for suggestions */
.max-h-48::-webkit-scrollbar {
  width: 6px;
}

.max-h-48::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.max-h-48::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.max-h-48::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Focus styles for better accessibility */
select:focus, input:focus {
  outline: none;
  ring: 2px;
  ring-color: #3b82f6;
  border-color: #3b82f6;
}

/* Animation for filter tags */
.inline-flex {
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Hover effects for interactive elements */
.hover\\:bg-gray-100:hover {
  background-color: #f3f4f6;
  transition: background-color 0.15s ease-in-out;
}

.hover\\:text-red-600:hover {
  color: #dc2626;
  transition: color 0.15s ease-in-out;
}

/* Custom styles for multi-select tags */
.bg-blue-100 {
  animation: slideIn 0.2s ease-in-out;
}

.bg-purple-100 {
  animation: slideIn 0.2s ease-in-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Improved filter panel shadow */
.shadow-lg {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* Better spacing for filter items */
.space-y-4 > * + * {
  margin-top: 1rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .min-w-96 {
    min-width: 100%;
  }
  
  .flex-wrap {
    flex-wrap: wrap;
  }
  
  .w-24 {
    width: 100%;
    margin-bottom: 0.5rem;
  }
  
  .w-28 {
    width: 100%;
    margin-bottom: 0.5rem;
  }
}
</style>