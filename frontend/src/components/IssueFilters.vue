<template>
  <div class="bg-white p-6 rounded-lg shadow-sm border mb-6">
    <div class="flex flex-col sm:flex-row gap-4">
      <!-- Search Input -->
      <div class="flex-1">
        <Input
          v-model="localSearchQuery"
          placeholder="Search"
          class="w-full"
          @input="handleSearchChange"
        />
      </div>
      
      <!-- Filter Controls -->
      <div class="flex gap-2 flex-wrap">
        <!-- Status Filter -->
        <Select
          v-model="localFilters.status"
          :options="statusOptions"
          placeholder="All Status"
          @change="handleFilterChange"
        />
        
        <!-- Priority Filter -->
        <Select
          v-model="localFilters.priority"
          :options="priorityOptions"
          placeholder="All Priority"
          @change="handleFilterChange"
        />
        
        <!-- Assignee Filter -->
        <Select
          v-model="localFilters.assignee"
          :options="assigneeOptions"
          placeholder="All Assignees"
          @change="handleFilterChange"
        />
        
        <!-- Tags Filter (Issue Type) -->
        <Select
          v-model="localFilters.tags"
          :options="tagsOptions"
          placeholder="All Tags"
          @change="handleFilterChange"
        />
        
        <!-- Sort By Filter -->
        <Select
          v-model="localFilters.sortBy"
          :options="sortOptions"
          placeholder="Sort By"
          @change="handleFilterChange"
        />
        
        <!-- New Issue Button -->
        <Button theme="blue" variant="solid" size="sm">
          New Issue
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, Input, Select } from "frappe-ui"
import { computed, ref, watch } from "vue"

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
})

// Emits
const emit = defineEmits(["update:searchQuery", "update:filters"])

// Local reactive state
const localSearchQuery = ref(props.searchQuery)
const localFilters = ref({ ...props.filters })

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

// Event handlers
const handleSearchChange = () => {
	emit("update:searchQuery", localSearchQuery.value)
}

const handleFilterChange = () => {
	emit("update:filters", { ...localFilters.value })
}
</script>