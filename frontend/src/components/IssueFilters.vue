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


    <!-- Filter Controls Section -->
    <div class="border-t border-gray-200 pt-6">
      <div class="mb-4">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">Filter Options</h3>
      </div>
      
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <!-- Status Filter -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 block">Status</label>
          <Select v-model="localFilters.status" :options="statusOptions"
            @change="handleFilterChange" class="w-full" />
        </div>

        <!-- Priority Filter -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 block">Priority</label>
          <Select v-model="localFilters.priority" :options="priorityOptions"
            @change="handleFilterChange" class="w-full" />
        </div>

        <!-- Assignee Filter -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 block">Assignee</label>
          <Select v-model="localFilters.assignee" :options="assigneeOptions"
            @change="handleFilterChange" class="w-full" />
        </div>

        <!-- Tags Filter (Issue Type) -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 block">Tags</label>
          <Select v-model="localFilters.tags" :options="tagsOptions"
            @change="handleFilterChange" class="w-full" />
        </div>

        <!-- Sort By Filter -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 block">Sort By</label>
          <Select v-model="localFilters.sortBy" :options="sortOptions" 
            @change="handleFilterChange" class="w-full" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Select } from "frappe-ui"
import { computed, ref, watch, onMounted, onUnmounted } from "vue"
import CustomSearchBox from "./CustomSearchBox.vue"

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
}

const handleSuggestionSelected = (suggestion) => {
  emit("suggestion-selected", suggestion)
}

const handleFilterChange = () => {
  emit("update:filters", { ...localFilters.value })
}

// Lifecycle hooks for keyboard shortcuts
onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcut)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcut)
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
</style>