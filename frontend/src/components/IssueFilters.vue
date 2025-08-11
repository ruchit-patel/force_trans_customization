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
            class="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors">
            Clear All
          </button>
          <button v-if="pendingFilters.length > 0"
            @click="applyFilters"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
              isApplyingFilters ? 'bg-blue-500 text-white cursor-wait' :
              hasPendingChanges ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-600 cursor-not-allowed'
            ]"
            :disabled="!hasPendingChanges || isApplyingFilters">
            <span v-if="isApplyingFilters" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Applying...
            </span>
            <span v-else>
              {{ hasPendingChanges ? 'Apply Filters' : 'Filters Applied' }}
            </span>
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
                  class="grid grid-cols-12 gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                  
                  <!-- Field Name -->
                  <div class="col-span-2 flex items-center">
                    <span class="text-sm font-semibold text-gray-800 bg-white px-2 py-1 rounded-md border border-gray-200">
                      {{ getFieldLabel(filter.field) }}
                    </span>
                  </div>

                  <!-- Operator -->
                  <div class="col-span-2 flex items-center">
                    <Dropdown 
                      :options="getOperatorDropdownOptions(filter.field, filter)"
                      :placement="'left'"
                    >
                      <template #default="{ open }">
                        <button 
                          :class="[
                            'w-full px-3 py-2 text-sm border rounded-md transition-all duration-200 flex items-center justify-between bg-white hover:bg-gray-50',
                            open ? 'border-blue-500 ring-2 ring-blue-200 shadow-md' : 'border-gray-300 hover:border-gray-400 shadow-sm'
                          ]"
                        >
                          <span class="text-gray-700 font-medium truncate">{{ getOperatorLabel(filter.operator, filter.field) }}</span>
                          <svg class="w-4 h-4 text-gray-400 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                          </svg>
                        </button>
                      </template>
                    </Dropdown>
                  </div>

                  <!-- Dynamic Value Input -->
                  <div class="col-span-7">
                    <!-- Text Input -->
                    <input v-if="getFieldType(filter.field) === 'text'" 
                      v-model="filter.value" 
                      type="text" 
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                    
                    <!-- Email Input -->
                    <input v-else-if="getFieldType(filter.field) === 'email'" 
                      v-model="filter.value" 
                      type="email" 
                      :placeholder="getFieldPlaceholder(filter.field)"
                      class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                    
                    <!-- DateTime Input -->
                    <div v-else-if="getFieldType(filter.field) === 'datetime'" class="space-y-2">
                      <div v-if="filter.operator === 'between'" class="grid grid-cols-2 gap-2">
                        <div>
                          <input v-model="filter.startValue" 
                            type="datetime-local" 
                            placeholder="Start date and time"
                            @input="updateDateRange(filter)"
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                          <p class="text-xs text-gray-500 mt-1">From</p>
                        </div>
                        <div>
                          <input v-model="filter.endValue" 
                            type="datetime-local" 
                            placeholder="End date and time"
                            @input="updateDateRange(filter)"
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                          <p class="text-xs text-gray-500 mt-1">To</p>
                        </div>
                      </div>
                      <div v-else>
                        <input v-model="filter.value" 
                          type="datetime-local" 
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                        <p class="text-xs text-gray-500 italic mt-1">Select date and time</p>
                      </div>
                    </div>

                    <!-- Date Input -->
                    <div v-else-if="getFieldType(filter.field) === 'date'" class="space-y-2">
                      <div v-if="filter.operator === 'between'" class="grid grid-cols-2 gap-2">
                        <div>
                          <input v-model="filter.startValue" 
                            type="date" 
                            @input="updateDateRange(filter)"
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                          <p class="text-xs text-gray-500 mt-1">From</p>
                        </div>
                        <div>
                          <input v-model="filter.endValue" 
                            type="date" 
                            @input="updateDateRange(filter)"
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                          <p class="text-xs text-gray-500 mt-1">To</p>
                        </div>
                      </div>
                      <div v-else>
                        <input v-model="filter.value" 
                          type="date" 
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                      </div>
                    </div>
                    
                    <!-- Select/ComboBox for Options -->
                    <div v-else-if="getFieldType(filter.field) === 'select'" class="relative">
                      <div v-if="!filter.isMultiSelect">
                        <!-- Simple select for priority field -->
                        <select v-if="filter.field === 'priority' || filter.field === 'status' || filter.field === 'issue_type'"
                          v-model="filter.value"
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400"
                        >
                          <option value="">Select {{ getFieldLabel(filter.field) }}...</option>
                          <option v-for="option in getFieldOptions(filter.field)" :key="option.value" :value="option.value">
                            {{ option.label }}
                          </option>
                        </select>
                      </div>
                      
                      <!-- Multi-select for tags, users, etc -->
                      <div v-else class="space-y-2">
                        <div v-if="getSelectedValues(filter.value).length > 0" class="flex flex-wrap gap-1 mb-2 p-2 bg-white rounded-md border border-gray-200">
                          <span v-for="(selectedValue, idx) in getSelectedValues(filter.value)" :key="idx"
                            class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full border border-blue-200 hover:bg-blue-200 transition-colors">
                            {{ getDisplayValueForOption(selectedValue, filter.field) }}
                            <button @click="removeSelectedValue(filter, idx)" class="ml-1 text-blue-600 hover:text-red-600 transition-colors">
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                              </svg>
                            </button>
                          </span>
                        </div>
                      </div>
                    </div>

                    <!-- Link/Reference Input with ComboBox -->
                    <div v-else-if="getFieldType(filter.field) === 'link'" class="space-y-2">
                      <!-- Multi-select for all link fields -->
                      <div class="space-y-2">
                        <!-- Selected Items Display -->
                        <div v-if="getSelectedValues(filter.value).length > 0" class="flex flex-wrap gap-1 mb-2 p-2 bg-white rounded-md border border-gray-200">
                          <span v-for="(selectedValue, idx) in getSelectedValues(filter.value)" :key="idx"
                            class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full border border-blue-200 hover:bg-blue-200 transition-colors">
                            {{ getDisplayValueForUser(selectedValue, filter) }}
                            <button @click="removeSelectedValue(filter, idx)" class="ml-1 text-blue-600 hover:text-red-600 transition-colors">
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                              </svg>
                            </button>
                          </span>
                        </div>
                        
                        <!-- Search Input -->
                        <div class="relative">
                          <input 
                            v-model="filter.searchValue" 
                            @input="handleLinkSearch(filter, filter.searchValue)"
                            type="text" 
                            :placeholder="`Search and add ${getFieldLabel(filter.field)}...`"
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                          
                          <!-- Loading indicator -->
                          <div v-if="filter.loading" class="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <svg class="animate-spin h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24">
                              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                          </div>
                        </div>
                        
                        <!-- Search Results Dropdown -->
                        <div v-if="filter.suggestions && filter.suggestions.length > 0 && filter.searchValue" 
                          class="max-h-48 overflow-y-auto border border-gray-200 rounded-md bg-white shadow-lg">
                          <button v-for="(suggestion, idx) in filter.suggestions" :key="idx"
                            @click="addUserToMultiSelect(filter, suggestion)"
                            class="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm border-b border-gray-100 last:border-b-0">
                            <div class="font-medium text-gray-900">{{ suggestion.label }}</div>
                            <div class="text-xs text-gray-500">{{ suggestion.subtitle }}</div>
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- Tags/Multi-value Input with Search -->
                    <div v-else-if="getFieldType(filter.field) === 'tags'" class="space-y-2">
                      <!-- Selected Tags Display -->
                      <div v-if="getTags(filter.value).length > 0" class="flex flex-wrap gap-1 mb-2 p-2 bg-white rounded-md border border-gray-200">
                        <span v-for="(tag, idx) in getTags(filter.value)" :key="idx"
                          class="inline-flex items-center px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full border border-purple-200 hover:bg-purple-200 transition-colors">
                          {{ tag }}
                          <button @click="removeTag(filter, idx)" class="ml-1 text-purple-600 hover:text-red-600 transition-colors">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                          </button>
                        </span>
                      </div>
                      
                      <!-- Tag Search Input -->
                      <div class="relative">
                        <input v-model="filter.tagInput" 
                          @input="handleTagSearch(filter, filter.tagInput)"
                          @keyup.enter="addTagFromInput(filter)"
                          @keyup.comma="addTagFromInput(filter)"
                          type="text" 
                          placeholder="Search and select tags or type new ones..."
                          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400" />
                        
                        <!-- Loading indicator -->
                        <div v-if="filter.loadingTags" class="absolute right-3 top-1/2 transform -translate-y-1/2">
                          <svg class="animate-spin h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        </div>
                      </div>
                      
                      <!-- Tag Suggestions Dropdown -->
                      <div v-if="filter.tagSuggestions && filter.tagSuggestions.length > 0" 
                        class="max-h-48 overflow-y-auto border border-gray-200 rounded-md bg-white shadow-lg">
                        <button v-for="(tagSuggestion, idx) in filter.tagSuggestions" :key="idx"
                          @click="addTagFromSuggestion(filter, tagSuggestion)"
                          class="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm border-b border-gray-100 last:border-b-0">
                          <div class="flex items-center justify-between">
                            <div>
                              <div class="font-medium text-gray-900">{{ tagSuggestion.label }}</div>
                              <div class="text-xs text-gray-500">{{ tagSuggestion.subtitle }}</div>
                            </div>
                            <div v-if="tagSuggestion.color" 
                              class="w-3 h-3 rounded-full border border-gray-300" 
                              :style="{ backgroundColor: tagSuggestion.color }"></div>
                          </div>
                        </button>
                      </div>
                      
                      <p class="text-xs text-gray-500 italic">Search existing tags or press Enter/comma to create new tags</p>
                    </div>
                  </div>

                  <!-- Remove Button -->
                  <div class="col-span-1 flex items-start justify-center pt-1">
                    <button @click="removeFilter(index)" 
                      class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-all duration-200 group">
                      <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Bottom Actions -->
              <div v-if="pendingFilters.length > 0" class="flex justify-between items-center pt-4 mt-4 border-t border-gray-200">
                <button @click="clearAllFilters" class="text-sm text-gray-600 hover:text-gray-900">
                  Clear All
                </button>
                <button @click="applyFilters" :disabled="!hasPendingChanges || isApplyingFilters"
                  :class="[
                    'px-4 py-2 text-sm font-medium rounded transition-all duration-200',
                    isApplyingFilters ? 'bg-gray-700 text-white cursor-wait' :
                    hasPendingChanges ? 'bg-gray-900 text-white hover:bg-gray-800' : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                  ]">
                  <span v-if="isApplyingFilters" class="flex items-center">
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Applying...
                  </span>
                  <span v-else>
                    {{ hasPendingChanges ? 'Apply Filters' : 'Filters Applied' }}
                  </span>
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
import { Dropdown, Combobox, Autocomplete } from "frappe-ui"
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
const emit = defineEmits(["update:searchQuery", "update:filters", "suggestion-selected", "filters-applied"])

// State
const searchQuery = ref(props.searchQuery)
const showFilterPanel = ref(false)
const pendingFilters = ref([])
const appliedFilters = ref([])
let filterIdCounter = 0

// Loading state for better UX
const isApplyingFilters = ref(false)

// Enhanced Field Configuration with Types - Only specified fields
const availableFields = [
  { value: 'subject', label: 'Subject', type: 'text' },
  { value: 'status', label: 'Status', type: 'select' },
  { value: 'raised_by', label: 'Raised By', type: 'email' },
  { value: 'description', label: 'Description', type: 'text' },
  { value: 'customer', label: 'Customer', type: 'link' },
  { value: 'contact', label: 'Contact', type: 'link' },
  { value: 'lead', label: 'Lead', type: 'link' },
  { value: 'custom_assigned_csm_team', label: 'Assigned CSM Team', type: 'link' },
  { value: 'custom_users_assigned', label: 'User Assigned', type: 'link' },
  { value: 'creation', label: 'Created Date', type: 'date' },
  { value: 'modified', label: 'Modified Date', type: 'date' },
  { value: '_user_tags', label: 'Tags', type: 'tags' },
]

// Field Options Data - Only for select type fields
const fieldOptions = {
  status: [
    { value: 'New', label: 'New' },
    { value: 'In Review', label: 'In Review' },
    { value: 'Confirmed', label: 'Confirmed' },
    { value: 'In Transit', label: 'In Transit' },
    { value: 'Delivered', label: 'Delivered' },
    { value: 'Closed', label: 'Closed' },
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
    { value: 'in', label: 'In' },
    { value: 'equals', label: 'Is' },
    { value: 'not_equals', label: 'Is Not' },
    { value: 'like', label: 'Contains' },
    { value: 'not_in', label: 'Not In' }
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

const isLinkFieldMultiSelect = (fieldValue) => {
  // All link fields are multiSelect by default
  return getFieldType(fieldValue) === 'link'
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
    customer: 'Search for customer...',
    contact: 'Search for contact...',
    lead: 'Search for lead...',
    custom_assigned_csm_team: 'Search for CSM team...',
    custom_users_assigned: 'Search for users...',
    creation: 'Select date',
    modified: 'Select date'
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

// New helper functions for enhanced functionality
const getDisplayValueForUser = (value, filter) => {
  if (filter.userDisplayMap && filter.userDisplayMap[value]) {
    return filter.userDisplayMap[value]
  }
  return value
}

const addUserToMultiSelect = (filter, suggestion) => {
  const currentValues = getSelectedValues(filter.value)
  if (!currentValues.includes(suggestion.value)) {
    currentValues.push(suggestion.value)
    filter.value = currentValues.join(', ')
    
    // Store display name mapping
    if (!filter.userDisplayMap) filter.userDisplayMap = {}
    filter.userDisplayMap[suggestion.value] = suggestion.label
  }
  filter.searchValue = ''
  filter.suggestions = []
}

// Tag search helpers
let tagSearchTimeouts = {}

const handleTagSearch = async (filter, searchValue) => {
  filter.loadingTags = true
  
  // Clear existing timeout for this filter
  if (tagSearchTimeouts[filter.id]) {
    clearTimeout(tagSearchTimeouts[filter.id])
  }
  
  // Debounce search requests
  tagSearchTimeouts[filter.id] = setTimeout(async () => {
    try {
      const response = await fetch('/api/method/force_trans_customization.api.issues.search_tags', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Frappe-CSRF-Token': window.csrf_token || ''
        },
        body: JSON.stringify({
          search_query: searchValue || '',
          limit: 15
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        filter.tagSuggestions = data.message || []
      }
    } catch (error) {
      console.error('Tag search error:', error)
      filter.tagSuggestions = []
    } finally {
      filter.loadingTags = false
    }
  }, 300) // 300ms debounce
}

const addTagFromInput = (filter) => {
  if (!filter.tagInput || !filter.tagInput.trim()) return
  
  const newTag = filter.tagInput.replace(',', '').trim()
  const currentTags = getTags(filter.value)
  
  if (newTag && !currentTags.includes(newTag)) {
    currentTags.push(newTag)
    filter.value = currentTags.join(', ')
  }
  
  filter.tagInput = ''
  filter.tagSuggestions = []
}

const addTagFromSuggestion = (filter, tagSuggestion) => {
  const currentTags = getTags(filter.value)
  
  if (!currentTags.includes(tagSuggestion.value)) {
    currentTags.push(tagSuggestion.value)
    filter.value = currentTags.join(', ')
  }
  
  filter.tagInput = ''
  filter.tagSuggestions = []
}

// Link/Reference Helpers - Updated to use real API endpoints
let searchTimeouts = {}

const handleLinkSearch = async (filter, searchValue) => {
  filter.searchValue = searchValue
  filter.loading = true
  
  // Clear existing timeout for this filter
  if (searchTimeouts[filter.id]) {
    clearTimeout(searchTimeouts[filter.id])
  }
  
  // Debounce search requests
  searchTimeouts[filter.id] = setTimeout(async () => {
    try {
      let searchResults = []
      let endpoint = ''
      
      // Determine which endpoint to use based on field type
      if (filter.field === 'customer') {
        endpoint = '/api/method/force_trans_customization.api.issues.search_customers'
      } else if (filter.field === 'contact') {
        endpoint = '/api/method/force_trans_customization.api.issues.search_contacts'
      } else if (filter.field === 'lead') {
        endpoint = '/api/method/force_trans_customization.api.issues.search_leads'
      } else if (filter.field === 'custom_assigned_csm_team') {
        endpoint = '/api/method/force_trans_customization.api.issues.search_user_groups'
      } else if (filter.field === 'custom_users_assigned') {
        endpoint = '/api/method/force_trans_customization.api.issues.search_users'
      }
      
      if (endpoint) {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': window.csrf_token || ''
          },
          body: JSON.stringify({
            search_query: searchValue || '',
            limit: 10,
            doctype_filter: filter.field === 'custom_users_assigned' ? 'User' : undefined
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          searchResults = data.message || []
        }
      }
      
      filter.suggestions = searchResults
    } catch (error) {
      console.error('Search error:', error)
      filter.suggestions = []
    } finally {
      filter.loading = false
    }
  }, 300) // 300ms debounce
}


// Frappe UI Helper Functions
const getOperatorDropdownOptions = (fieldValue, filter) => {
  const operators = getOperatorsForField(fieldValue)
  return operators.map(op => ({
    label: op.label,
    onClick: () => {
      // Only clear specific values based on operator change, preserve main data
      if (filter.operator !== op.value) {
        // For date fields, only clear date range specific values
        if (getFieldType(fieldValue) === 'date') {
          if (op.value === 'between') {
            // Switching to between - keep single value as start value
            if (filter.value && !filter.startValue) {
              filter.startValue = filter.value
              filter.endValue = ''
            }
          } else if (filter.operator === 'between') {
            // Switching from between - use start value as main value
            if (filter.startValue && !filter.value) {
              filter.value = filter.startValue
            }
            filter.startValue = ''
            filter.endValue = ''
          }
        }
        
        // Don't clear main filter values - preserve user input
        // Only clear operator-specific UI state
        filter.multiSelectValue = null
        filter.searchValue = ''
        
        // Clear search suggestions but keep selected values
        filter.suggestions = []
        filter.searchOptions = []
      }
      filter.operator = op.value
    }
  }))
}

const getOperatorLabel = (operatorValue, fieldValue) => {
  const operators = getOperatorsForField(fieldValue)
  return operators.find(op => op.value === operatorValue)?.label || operatorValue
}

const getComboboxOptions = (fieldValue) => {
  const options = getFieldOptions(fieldValue)
  if (!options || options.length === 0) {
    return []
  }
  return options.map(option => {
    if (typeof option === 'string') {
      return {
        label: option,
        value: option
      }
    }
    return {
      label: option.label || option.value,
      value: option.value || option.label
    }
  })
}

const getDisplayValueForOption = (value, fieldValue) => {
  const options = getFieldOptions(fieldValue)
  const option = options.find(opt => opt.value === value)
  return option ? option.label : value
}

const getAvailableComboboxOptions = (filter) => {
  const allOptions = getFieldOptions(filter.field)
  const selectedValues = getSelectedValues(filter.value)
  return allOptions
    .filter(option => !selectedValues.includes(option.value))
    .map(option => ({
      label: option.label,
      value: option.value
    }))
}

const handleMultiSelectChange = (filter, newValue) => {
  if (!newValue) return
  
  const values = getSelectedValues(filter.value)
  if (!values.includes(newValue)) {
    values.push(newValue)
    filter.value = values.join(', ')
  }
  // Clear the combobox selection
  filter.multiSelectValue = null
}


const updateDateRange = (filter) => {
  if (filter.startValue && filter.endValue) {
    filter.value = `${filter.startValue},${filter.endValue}`
  } else {
    filter.value = ''
  }
}

// Main Functions
const addFilter = (fieldValue) => {
  // Set default operators based on field type
  const fieldType = getFieldType(fieldValue)
  let defaultOperator = 'equals'
  
  if (fieldType === 'link') {
    defaultOperator = 'in' // Default to 'In' for link fields
  } else if (fieldType === 'tags') {
    defaultOperator = 'has' // Default to 'Has Tag' for tags
  } else {
    defaultOperator = getOperatorsForField(fieldValue)[0]?.value || 'equals'
  }
  
  const newFilter = {
    id: ++filterIdCounter,
    field: fieldValue,
    operator: defaultOperator,
    value: '',
    // Date range specific properties
    startValue: '',
    endValue: '',
    // Link-specific properties (all link fields are multiSelect)
    searchValue: '',
    displayValue: '',
    suggestions: [],
    showSuggestions: false,
    loading: false,
    userDisplayMap: {},
    // Tags-specific properties
    tagInput: '',
    tagSuggestions: [],
    loadingTags: false
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

const applyFilters = async () => {
  if (!hasPendingChanges.value) return
  
  // Show loading state
  isApplyingFilters.value = true
  
  try {
    appliedFilters.value = JSON.parse(JSON.stringify(pendingFilters.value))
    emitFilters()
    showFilterPanel.value = false
  } catch (error) {
    console.error('Error applying filters:', error)
  } finally {
    // Add slight delay for smooth UX
    setTimeout(() => {
      isApplyingFilters.value = false
    }, 500)
  }
}

const clearAllFilters = () => {
  pendingFilters.value = []
  appliedFilters.value = []
  searchQuery.value = ''
  
  emit("update:searchQuery", '')
  emit("update:filters", [])
  emit("filters-applied", [])
  
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
  
  console.log('Emitting filters:', filterData)
  
  // Emit both the old format (for compatibility) and new event
  emit("update:filters", filterData)
  emit("filters-applied", filterData)
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

// Load from localStorage on mount and setup search for link fields
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

  // Setup reactive search for link fields
  watch(() => pendingFilters.value, (newFilters) => {
    newFilters.forEach(filter => {
      if (getFieldType(filter.field) === 'link' && filter.searchValue) {
        handleLinkSearch(filter, filter.searchValue)
      }
    })
  }, { deep: true })
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

/* Enhanced filter container styling */
.filter-container {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
}

.filter-container:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
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

/* Frappe UI Combobox styling improvements */
.filter-combobox {
  @apply relative;
}

.filter-combobox .reka-combobox-trigger {
  @apply bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-200 shadow-sm hover:shadow-md;
}

/* Grid layout improvements */
.grid-cols-12 {
  grid-template-columns: repeat(12, minmax(0, 1fr));
}

/* Enhanced button styling */
button:focus {
  outline: 2px solid transparent;
  outline-offset: 2px;
}

/* Tag styling improvements */
.inline-flex {
  animation: fadeIn 0.3s ease-out;
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .grid-cols-12 {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
  
  .col-span-2,
  .col-span-7,
  .col-span-1 {
    grid-column: span 1;
  }
  
  .min-w-96 {
    min-width: 100%;
  }
}

@media (max-width: 768px) {
  .filter-panel-grid {
    display: block;
  }
  
  .filter-panel-grid > * {
    margin-bottom: 0.75rem;
  }
  
  .flex-wrap {
    flex-wrap: wrap;
  }
}
</style>