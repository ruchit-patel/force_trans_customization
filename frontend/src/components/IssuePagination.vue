<template>
  <div class="bg-white rounded-lg shadow-sm border mt-4">
    <div class="px-6 py-4 flex items-center justify-between">
      <!-- Results info -->
      <div class="text-sm text-gray-700">
        <span v-if="totalItems > 0">
          Showing {{ startItem }} to {{ endItem }} of {{ totalItems }} results
        </span>
        <span v-else>
          No results found
        </span>
      </div>

      <!-- Pagination controls -->
      <div class="flex items-center space-x-2" v-if="totalPages > 1">
        <!-- Previous button -->
        <Button
          theme="gray"
          variant="outline"
          size="sm"
          :disabled="currentPage === 1"
          @click="goToPreviousPage"
        >
          <template #prefix>
            <FeatherIcon name="chevron-left" class="h-4 w-4" />
          </template>
          Previous
        </Button>

        <!-- Page numbers -->
        <div class="flex items-center space-x-1">
          <!-- First page -->
          <Button
            v-if="showFirstPage"
            theme="gray"
            variant="outline"
            size="sm"
            :class="{ 'bg-blue-50 text-blue-600 border-blue-200': currentPage === 1 }"
            @click="goToPage(1)"
          >
            1
          </Button>

          <!-- First ellipsis -->
          <span v-if="showFirstEllipsis" class="px-2 text-gray-500">...</span>

          <!-- Visible page numbers -->
          <Button
            v-for="page in visiblePages"
            :key="page"
            theme="gray"
            variant="outline"
            size="sm"
            :class="{ 'bg-blue-50 text-blue-600 border-blue-200': currentPage === page }"
            @click="goToPage(page)"
          >
            {{ page }}
          </Button>

          <!-- Last ellipsis -->
          <span v-if="showLastEllipsis" class="px-2 text-gray-500">...</span>

          <!-- Last page -->
          <Button
            v-if="showLastPage"
            theme="gray"
            variant="outline"
            size="sm"
            :class="{ 'bg-blue-50 text-blue-600 border-blue-200': currentPage === totalPages }"
            @click="goToPage(totalPages)"
          >
            {{ totalPages }}
          </Button>
        </div>

        <!-- Next button -->
        <Button
          theme="gray"
          variant="outline"
          size="sm"
          :disabled="currentPage === totalPages"
          @click="goToNextPage"
        >
          Next
          <template #suffix>
            <FeatherIcon name="chevron-right" class="h-4 w-4" />
          </template>
        </Button>
      </div>

      <!-- Items per page selector -->
      <div class="flex items-center space-x-2" v-if="showItemsPerPage">
        <span class="text-sm text-gray-700">Items per page:</span>
        <Select
          v-model="localItemsPerPage"
          :options="itemsPerPageOptions"
          @change="handleItemsPerPageChange"
          class="w-20"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FeatherIcon, Select } from "frappe-ui"
import { computed, ref, watch } from "vue"

// Props
const props = defineProps({
	currentPage: {
		type: Number,
		default: 1,
	},
	totalItems: {
		type: Number,
		default: 0,
	},
	itemsPerPage: {
		type: Number,
		default: 10,
	},
	showItemsPerPage: {
		type: Boolean,
		default: true,
	},
	maxVisiblePages: {
		type: Number,
		default: 5,
	},
})

// Emits
const emit = defineEmits([
	"update:currentPage",
	"update:itemsPerPage",
	"pageChange",
])

// Local state
const localItemsPerPage = ref(props.itemsPerPage)

// Watch for prop changes
watch(
	() => props.itemsPerPage,
	(newValue) => {
		localItemsPerPage.value = newValue
	},
)

// Computed properties
const totalPages = computed(() => {
	return Math.ceil(props.totalItems / props.itemsPerPage)
})

const startItem = computed(() => {
	if (props.totalItems === 0) return 0
	return (props.currentPage - 1) * props.itemsPerPage + 1
})

const endItem = computed(() => {
	const end = props.currentPage * props.itemsPerPage
	return Math.min(end, props.totalItems)
})

// Calculate visible page numbers
const visiblePages = computed(() => {
	const pages = []
	const maxVisible = props.maxVisiblePages
	const current = props.currentPage
	const total = totalPages.value

	if (total <= maxVisible) {
		// Show all pages if total is less than max visible
		for (let i = 1; i <= total; i++) {
			pages.push(i)
		}
	} else {
		// Calculate start and end of visible range
		let start = Math.max(1, current - Math.floor(maxVisible / 2))
		let end = Math.min(total, start + maxVisible - 1)

		// Adjust start if we're near the end
		if (end - start + 1 < maxVisible) {
			start = Math.max(1, end - maxVisible + 1)
		}

		// Don't include first and last page in visible range if they'll be shown separately
		if (start > 1) start = Math.max(2, start)
		if (end < total) end = Math.min(total - 1, end)

		for (let i = start; i <= end; i++) {
			pages.push(i)
		}
	}

	return pages
})

// Show/hide first page button
const showFirstPage = computed(() => {
	return (
		totalPages.value > props.maxVisiblePages && !visiblePages.value.includes(1)
	)
})

// Show/hide last page button
const showLastPage = computed(() => {
	return (
		totalPages.value > props.maxVisiblePages &&
		!visiblePages.value.includes(totalPages.value)
	)
})

// Show/hide ellipsis
const showFirstEllipsis = computed(() => {
	return (
		showFirstPage.value &&
		visiblePages.value.length > 0 &&
		visiblePages.value[0] > 2
	)
})

const showLastEllipsis = computed(() => {
	return (
		showLastPage.value &&
		visiblePages.value.length > 0 &&
		visiblePages.value[visiblePages.value.length - 1] < totalPages.value - 1
	)
})

// Items per page options
const itemsPerPageOptions = computed(() => [
	{ label: "5", value: 5 },
	{ label: "10", value: 10 },
	{ label: "20", value: 20 },
	{ label: "50", value: 50 },
	{ label: "100", value: 100 },
])

// Methods
const goToPage = (page) => {
	if (page >= 1 && page <= totalPages.value && page !== props.currentPage) {
		emit("update:currentPage", page)
		emit("pageChange", {
			page,
			itemsPerPage: props.itemsPerPage,
			offset: (page - 1) * props.itemsPerPage,
		})
	}
}

const goToPreviousPage = () => {
	if (props.currentPage > 1) {
		goToPage(props.currentPage - 1)
	}
}

const goToNextPage = () => {
	if (props.currentPage < totalPages.value) {
		goToPage(props.currentPage + 1)
	}
}

const handleItemsPerPageChange = () => {
	const newItemsPerPage = localItemsPerPage.value
	emit("update:itemsPerPage", newItemsPerPage)

	// Calculate new page to maintain roughly the same position
	const currentFirstItem = (props.currentPage - 1) * props.itemsPerPage + 1
	const newPage = Math.ceil(currentFirstItem / newItemsPerPage)

	emit("pageChange", {
		page: newPage,
		itemsPerPage: newItemsPerPage,
		offset: (newPage - 1) * newItemsPerPage,
	})
}
</script>