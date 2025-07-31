<template>
	<div class="relative w-full max-w-2xl mx-auto">
		<!-- Search Input Container -->
		<div class="relative group">
			<!-- Search Icon -->
			<div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none z-10">
				<svg class="h-5 w-5 text-slate-400 transition-colors duration-200 group-focus-within:text-blue-500"
					fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
			</div>

			<!-- Main Search Input -->
			<input ref="searchInput" type="text" v-model="searchQuery" @input="handleSearch" @focus="handleFocus"
				@blur="handleBlur" @keydown="handleKeydown" :placeholder="placeholder" class="w-full h-14 pl-12 pr-20 text-base bg-white border border-slate-200 rounded-2xl 
                       placeholder-slate-400 text-slate-700 transition-all duration-200 ease-out
                       focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 
                       focus:bg-white hover:border-slate-300 hover:shadow-sm focus:shadow-lg
                       backdrop-blur-sm" :class="{
						'shadow-lg ring-2 ring-blue-500/20 border-blue-500': isFocused,
						'bg-slate-50/50': !isFocused && searchQuery
					}" />

			<!-- Right Side Controls -->
			<div class="absolute inset-y-0 right-0 flex items-center pr-4 space-x-2">
				<!-- Clear Button -->
				<button v-if="searchQuery" @click="clearSearch" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg 
                           transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
					aria-label="Clear search">
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
							d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>

				<!-- Keyboard Shortcut Hint -->
				<div v-if="!searchQuery && !isFocused" class="flex items-center pointer-events-none">
					<kbd class="hidden sm:inline-flex items-center px-2.5 py-1.5 border border-slate-200 
                               rounded-lg text-xs font-mono text-slate-400 bg-slate-50/80 shadow-sm">
						<span class="text-xs">⌘</span>K
					</kbd>
				</div>

				<!-- Loading Spinner -->
				<div v-if="isLoading" class="animate-spin">
					<svg class="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4">
						</circle>
						<path class="opacity-75" fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
						</path>
					</svg>
				</div>
			</div>
		</div>

		<!-- Search Results Dropdown -->
		<div v-if="showSuggestions" class="absolute z-50 w-full mt-3 bg-white border border-slate-200 rounded-2xl shadow-2xl 
                    overflow-hidden backdrop-blur-sm bg-white/95"
			:class="{ 'animate-in slide-in-from-top-2 duration-200': showSuggestions }">

			<!-- Results Header -->
			<div v-if="searchSuggestions.length > 0"
				class="px-4 py-3 bg-gradient-to-r from-slate-50 to-slate-100/50 border-b border-slate-100">
				<div class="flex items-center justify-between">
					<span class="text-xs font-semibold text-slate-600 uppercase tracking-wider">
						{{ searchSuggestions.length }} Result{{ searchSuggestions.length !== 1 ? 's' : '' }}
					</span>
					<span class="text-xs text-slate-500">
						{{ Math.round(searchTime) }}ms
					</span>
				</div>
			</div>

			<!-- Search Results -->
			<div class="max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
				<div v-if="searchSuggestions.length === 0 && searchQuery.length >= 2" class="px-6 py-8 text-center">
					<div class="w-16 h-16 mx-auto mb-4 bg-slate-100 rounded-full flex items-center justify-center">
						<svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
								d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
					</div>
					<p class="text-slate-500 text-sm font-medium">No issues found</p>
					<p class="text-slate-400 text-xs mt-1">Try adjusting your search terms</p>
				</div>

				<div v-for="(suggestion, index) in searchSuggestions" :key="suggestion.name || index"
					@click="selectSuggestion(suggestion)" class="group px-4 py-4 hover:bg-blue-50/50 cursor-pointer transition-all duration-150 
                            border-b border-slate-50 last:border-b-0" :class="{
								'bg-blue-50 ring-2 ring-blue-500/10': index === selectedSuggestionIndex
							}">
					<div class="flex items-start space-x-4">
						<!-- Issue Icon -->
						<div class="flex-shrink-0 mt-0.5">
							<div class="w-10 h-10 bg-gradient-to-br from-blue-100 to-blue-200 rounded-xl 
                                        flex items-center justify-center group-hover:from-blue-200 group-hover:to-blue-300 
                                        transition-all duration-200">
								<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor"
									viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
										d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
							</div>
						</div>

						<!-- Issue Content -->
						<div class="flex-1 min-w-0">
							<div class="flex items-start justify-between">
								<div class="flex-1 min-w-0">
									<h4 class="text-sm font-semibold text-slate-900 truncate group-hover:text-blue-900 
                                               transition-colors duration-150">
										<span
											v-html="highlightMatch(suggestion.subject || suggestion.name, searchQuery)"></span>
									</h4>
									<p class="text-xs text-slate-500 mt-1 line-clamp-2">
										ID: {{ suggestion.name }}
										<span v-if="suggestion.customer" class="ml-2">• {{ suggestion.customer }}</span>
									</p>
								</div>

								<!-- Status Badge -->
								<div class="flex-shrink-0 ml-4">
									<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium 
                                                 transition-colors duration-150"
										:class="getStatusBadgeClass(suggestion.status)">
										{{ suggestion.status }}
									</span>
								</div>
							</div>

							<!-- Additional Info -->
							<div v-if="suggestion.raised_by" class="mt-2 flex items-center text-xs text-slate-400">
								<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
										d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
								</svg>
								{{ suggestion.raised_by }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Footer with shortcuts -->
			<div v-if="searchQuery && searchSuggestions.length > 0"
				class="px-4 py-3 bg-slate-50/50 border-t border-slate-100">
				<div class="flex items-center justify-between text-xs text-slate-500">
					<div class="flex items-center space-x-4">
						<span class="flex items-center">
							<kbd
								class="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-xs font-mono mr-1">↵</kbd>
							to select
						</span>
						<span class="flex items-center">
							<kbd
								class="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-xs font-mono mr-1">↑↓</kbd>
							to navigate
						</span>
					</div>
					<span class="flex items-center">
						<kbd
							class="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-xs font-mono mr-1">esc</kbd>
						to close
					</span>
				</div>
			</div>
		</div>

		<!-- Backdrop -->
		<div v-if="showSuggestions" class="fixed inset-0 z-40 bg-black/5" @click="hideSuggestions">
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { searchIssues } from '../data/issues'

const props = defineProps({
	modelValue: {
		type: String,
		default: ''
	},
	placeholder: {
		type: String,
		default: 'Search issues by title, description, ID...'
	},
	issues: {
		type: Array,
		default: () => []
	}
})

const emit = defineEmits(['update:modelValue', 'search', 'suggestion-selected'])

const searchInput = ref(null)
const searchQuery = ref(props.modelValue)
const isFocused = ref(false)
const showSuggestions = ref(false)
const selectedSuggestionIndex = ref(-1)
const isLoading = ref(false)
const searchTime = ref(0)

// Watch for external changes to modelValue
watch(() => props.modelValue, (newValue) => {
	searchQuery.value = newValue
})

// Watch for changes in search query
watch(searchQuery, (newValue) => {
	emit('update:modelValue', newValue)
	emit('search', newValue)
})

// Search suggestions from API
const searchSuggestions = ref([])

// Function to fetch search suggestions from API
const fetchSearchSuggestions = async (query) => {
	if (!query || query.length < 2) {
		searchSuggestions.value = []
		return
	}

	try {
		isLoading.value = true
		const startTime = performance.now()

		const results = await searchIssues(query, 8)

		searchTime.value = performance.now() - startTime
		searchSuggestions.value = results || []

	} catch (error) {
		console.error('Search error:', error)
		searchSuggestions.value = []
	} finally {
		isLoading.value = false
	}
}

const handleSearch = () => {
	selectedSuggestionIndex.value = -1

	if (searchQuery.value.length >= 2) {
		fetchSearchSuggestions(searchQuery.value)
		showSuggestions.value = true
	} else {
		searchSuggestions.value = []
		showSuggestions.value = false
	}
}

// Highlight matching text in search results
const highlightMatch = (text, query) => {
	if (!text || !query) return text

	const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
	const regex = new RegExp(`(${escapedQuery})`, 'gi')
	return text.replace(regex, '<mark class="bg-yellow-200 text-yellow-900 px-0.5 rounded">$1</mark>')
}

// Get status badge styling
const getStatusBadgeClass = (status) => {
	const statusClasses = {
		'Open': 'bg-green-100 text-green-800 border border-green-200',
		'New': 'bg-blue-100 text-blue-800 border border-blue-200',
		'In Progress': 'bg-blue-100 text-blue-800 border border-blue-200',
		'In Review': 'bg-orange-100 text-orange-800 border border-orange-200',
		'Resolved': 'bg-gray-100 text-gray-800 border border-gray-200',
		'Closed': 'bg-red-100 text-red-800 border border-red-200',
		'Pending': 'bg-yellow-100 text-yellow-800 border border-yellow-200',
		'On Hold': 'bg-orange-100 text-orange-800 border border-orange-200',
		'Delivered': 'bg-green-100 text-green-800 border border-green-200',
		'Confirmed': 'bg-purple-100 text-purple-800 border border-purple-200'
	}

	return statusClasses[status] || 'bg-gray-100 text-gray-800 border border-gray-200'
}

const handleFocus = () => {
	isFocused.value = true
	if (searchQuery.value.length >= 2) {
		fetchSearchSuggestions(searchQuery.value)
		showSuggestions.value = true
	}
}

const handleBlur = () => {
	isFocused.value = false
	// Delay hiding suggestions to allow for click events
	setTimeout(() => {
		showSuggestions.value = false
	}, 200)
}

const handleKeydown = (event) => {
	if (!showSuggestions.value) return

	switch (event.key) {
		case 'ArrowDown':
			event.preventDefault()
			selectedSuggestionIndex.value = Math.min(
				selectedSuggestionIndex.value + 1,
				searchSuggestions.value.length - 1
			)
			break
		case 'ArrowUp':
			event.preventDefault()
			selectedSuggestionIndex.value = Math.max(selectedSuggestionIndex.value - 1, -1)
			break
		case 'Enter':
			event.preventDefault()
			if (selectedSuggestionIndex.value >= 0) {
				selectSuggestion(searchSuggestions.value[selectedSuggestionIndex.value])
			}
			break
		case 'Escape':
			hideSuggestions()
			searchInput.value?.blur()
			break
	}

}

const selectSuggestion = (suggestion) => {
	searchQuery.value = suggestion.name
	hideSuggestions()
	emit('suggestion-selected', suggestion)
}

const clearSearch = () => {
	searchQuery.value = ''
	hideSuggestions()
	searchInput.value?.focus()
}

const hideSuggestions = () => {
	showSuggestions.value = false
	selectedSuggestionIndex.value = -1
}

// Global keyboard shortcut (Cmd+K / Ctrl+K)
const handleGlobalKeydown = (event) => {
	if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
		event.preventDefault()
		searchInput.value?.focus()
		searchInput.value?.select()
	}
}

onMounted(() => {
	document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
	document.removeEventListener('keydown', handleGlobalKeydown)
})

// Expose methods for parent component
defineExpose({
	focus: () => {
		searchInput.value?.focus()
		searchInput.value?.select()
	},
	select: () => searchInput.value?.select(),
	$el: searchInput
})
</script>

<style scoped>
/* Custom scrollbar styles */
.scrollbar-thin {
	scrollbar-width: thin;
}

.scrollbar-thumb-slate-200::-webkit-scrollbar-thumb {
	background-color: rgb(226 232 240);
	border-radius: 0.375rem;
}

.scrollbar-track-transparent::-webkit-scrollbar-track {
	background-color: transparent;
}

.scrollbar-thin::-webkit-scrollbar {
	width: 6px;
}

/* Animation classes */
@keyframes slide-in-from-top {
	from {
		opacity: 0;
		transform: translateY(-10px);
	}

	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.animate-in {
	animation-fill-mode: both;
}

.slide-in-from-top-2 {
	animation-name: slide-in-from-top;
}

.duration-200 {
	animation-duration: 200ms;
}

/* Line clamp utility */
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

/* Focus ring improvements */
.focus\:ring-blue-500\/20:focus {
	--tw-ring-color: rgb(59 130 246 / 0.2);
}

/* Backdrop blur support */
.backdrop-blur-sm {
	backdrop-filter: blur(4px);
}

/* Background opacity utilities */
.bg-white\/95 {
	background-color: rgb(255 255 255 / 0.95);
}

.bg-slate-50\/50 {
	background-color: rgb(248 250 252 / 0.5);
}

.bg-slate-50\/80 {
	background-color: rgb(248 250 252 / 0.8);
}

.bg-blue-50\/50 {
	background-color: rgb(239 246 255 / 0.5);
}

.bg-black\/5 {
	background-color: rgb(0 0 0 / 0.05);
}

.ring-blue-500\/10 {
	--tw-ring-color: rgb(59 130 246 / 0.1);
}

.ring-blue-500\/20 {
	--tw-ring-color: rgb(59 130 246 / 0.2);
}
</style>