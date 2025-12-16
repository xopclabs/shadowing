<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'

const props = defineProps<{
  initialPath?: string
  videosOnly?: boolean
}>()

const emit = defineEmits<{
  (e: 'file-selected', path: string): void
}>()

interface FileInfo {
  name: string
  path: string
  is_dir: boolean
  size?: number
  extension?: string
}

interface DirectoryListing {
  path: string
  parent?: string
  files: FileInfo[]
}

// Ensure path ends with slash for directories
const ensureTrailingSlash = (path: string): string => {
  return path.endsWith('/') ? path : path + '/'
}

// State
const currentPath = ref(props.initialPath || '/mnt')
const pathInput = ref(ensureTrailingSlash(props.initialPath || '/mnt'))
const listing = ref<DirectoryListing | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Autocomplete state
const showAutocomplete = ref(false)
const autocompleteItems = ref<FileInfo[]>([])
const selectedAutocompleteIndex = ref(0)
const pathInputRef = ref<HTMLInputElement | null>(null)

// Quick navigation paths - verbose full paths
const quickPaths = [
  { name: '/', path: '/' },
  { name: '/home', path: '/home' },
  { name: '/mnt', path: '/mnt' },
]

// Format file size
const formatSize = (bytes?: number): string => {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

// Fuzzy match score - higher is better
const fuzzyScore = (name: string, pattern: string): number => {
  const nameLower = name.toLowerCase()
  const patternLower = pattern.toLowerCase()
  
  // Exact prefix match gets highest score
  if (nameLower.startsWith(patternLower)) {
    return 1000 + (patternLower.length / nameLower.length) * 100
  }
  
  // Check if all pattern characters exist in order (fuzzy)
  let score = 0
  let patternIdx = 0
  let consecutiveBonus = 0
  
  for (let i = 0; i < nameLower.length && patternIdx < patternLower.length; i++) {
    if (nameLower[i] === patternLower[patternIdx]) {
      score += 10 + consecutiveBonus
      consecutiveBonus += 5 // Bonus for consecutive matches
      patternIdx++
    } else {
      consecutiveBonus = 0
    }
  }
  
  // All pattern characters must be found
  if (patternIdx < patternLower.length) {
    return 0
  }
  
  // Bonus for shorter names (more relevant)
  score += Math.max(0, 50 - nameLower.length)
  
  return score
}

// Load directory
const loadDirectory = async (path: string, updateInput = true) => {
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams({ 
      path,
      videos_only: props.videosOnly ? 'true' : 'false',
    })
    
    const response = await fetch(`/api/files?${params}`)
    
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to load directory')
    }
    
    listing.value = await response.json()
    currentPath.value = path
    if (updateInput) {
      pathInput.value = ensureTrailingSlash(path)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load directory'
    console.error(e)
  } finally {
    loading.value = false
  }
}

// Load autocomplete suggestions with fuzzy matching
const loadAutocomplete = async (inputPath: string) => {
  if (!inputPath || inputPath.length < 1) {
    autocompleteItems.value = []
    showAutocomplete.value = false
    return
  }

  // Determine parent directory and partial name
  const lastSlash = inputPath.lastIndexOf('/')
  const parentPath = lastSlash === 0 ? '/' : inputPath.substring(0, lastSlash) || '/'
  const partial = inputPath.substring(lastSlash + 1)

  // If partial is empty (path ends with /), don't show autocomplete yet
  if (!partial) {
    autocompleteItems.value = []
    showAutocomplete.value = false
    return
  }

  try {
    const params = new URLSearchParams({ 
      path: parentPath,
      videos_only: 'false', // Show all for navigation
    })
    
    const response = await fetch(`/api/files?${params}`)
    
    if (!response.ok) {
      autocompleteItems.value = []
      return
    }
    
    const data: DirectoryListing = await response.json()
    
    // Score and filter items using fuzzy matching
    let scoredItems = data.files
      .filter(f => {
        if (!f.is_dir && props.videosOnly) {
          const videoExts = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v']
          if (!f.extension || !videoExts.includes(f.extension)) return false
        }
        return true
      })
      .map(f => ({
        file: f,
        score: fuzzyScore(f.name, partial)
      }))
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)

    autocompleteItems.value = scoredItems.slice(0, 10).map(item => item.file)
    selectedAutocompleteIndex.value = 0
    showAutocomplete.value = autocompleteItems.value.length > 0
  } catch (e) {
    autocompleteItems.value = []
    showAutocomplete.value = false
  }
}

// Handle path input changes
const onPathInputChange = () => {
  loadAutocomplete(pathInput.value)
}

// Handle focus - move cursor to end
const onPathFocus = () => {
  nextTick(() => {
    if (pathInputRef.value) {
      const len = pathInputRef.value.value.length
      pathInputRef.value.setSelectionRange(len, len)
    }
  })
  loadAutocomplete(pathInput.value)
}

// Handle keyboard navigation in path input (zsh-like behavior)
const onPathKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    
    if (autocompleteItems.value.length === 0) return
    
    if (autocompleteItems.value.length === 1) {
      // Only one match - auto-confirm it
      const item = autocompleteItems.value[0]
      confirmSelection(item)
    } else {
      // Multiple matches - cycle through (Shift+Tab goes backwards)
      if (e.shiftKey) {
        selectedAutocompleteIndex.value = 
          (selectedAutocompleteIndex.value - 1 + autocompleteItems.value.length) % autocompleteItems.value.length
      } else {
        selectedAutocompleteIndex.value = 
          (selectedAutocompleteIndex.value + 1) % autocompleteItems.value.length
      }
      // Preview selection in input
      const item = autocompleteItems.value[selectedAutocompleteIndex.value]
      pathInput.value = item.path
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (autocompleteItems.value.length > 0) {
      selectedAutocompleteIndex.value = 
        (selectedAutocompleteIndex.value + 1) % autocompleteItems.value.length
      // Preview selection in input
      const item = autocompleteItems.value[selectedAutocompleteIndex.value]
      pathInput.value = item.path
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (autocompleteItems.value.length > 0) {
      selectedAutocompleteIndex.value = 
        (selectedAutocompleteIndex.value - 1 + autocompleteItems.value.length) % autocompleteItems.value.length
      // Preview selection in input
      const item = autocompleteItems.value[selectedAutocompleteIndex.value]
      pathInput.value = item.path
    }
  } else if (e.key === '/' || e.key === 'Enter') {
    // Slash or Enter confirms the current selection
    if (autocompleteItems.value.length > 0) {
      e.preventDefault()
      const item = autocompleteItems.value[selectedAutocompleteIndex.value]
      confirmSelection(item)
    } else if (e.key === 'Enter') {
      // No autocomplete - just navigate to the typed path
      e.preventDefault()
      navigateToPath(pathInput.value)
    }
    // If '/' with no autocomplete, let it type normally
  } else if (e.key === 'Escape') {
    showAutocomplete.value = false
  }
}

// Confirm and apply the selected autocomplete item
const confirmSelection = (item: FileInfo) => {
  showAutocomplete.value = false
  
  if (item.is_dir) {
    // Auto-add slash for directories
    pathInput.value = item.path + '/'
    loadDirectory(item.path, false)
    // Position cursor at end and prepare for more typing
    nextTick(() => {
      loadAutocomplete(pathInput.value)
      pathInputRef.value?.focus()
    })
  } else {
    // It's a file - emit selection
    pathInput.value = item.path
    emit('file-selected', item.path)
  }
}

// Apply autocomplete selection (for click)
const applyAutocomplete = (item: FileInfo) => {
  confirmSelection(item)
}

// Navigate to typed path
const navigateToPath = (path: string) => {
  // Clean up path
  let cleanPath = path.trim()
  if (cleanPath.endsWith('/') && cleanPath.length > 1) {
    cleanPath = cleanPath.slice(0, -1)
  }
  if (!cleanPath.startsWith('/')) {
    cleanPath = '/' + cleanPath
  }
  
  showAutocomplete.value = false
  loadDirectory(cleanPath)
}

// Navigate to directory (from UI clicks - no autocomplete)
const navigateTo = (path: string) => {
  showAutocomplete.value = false
  pathInput.value = ensureTrailingSlash(path)
  loadDirectory(path)
}

// Go to parent directory (from UI click - no autocomplete)
const goUp = () => {
  if (listing.value?.parent) {
    showAutocomplete.value = false
    navigateTo(listing.value.parent)
  }
}

// Handle file/directory click (from UI - no autocomplete)
const handleClick = (file: FileInfo) => {
  showAutocomplete.value = false
  if (file.is_dir) {
    navigateTo(file.path)
  } else {
    emit('file-selected', file.path)
  }
}

// Get file icon based on extension
const getFileIcon = (file: FileInfo): string => {
  if (file.is_dir) return '📁'
  
  const videoExts = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v']
  if (file.extension && videoExts.includes(file.extension)) {
    return '🎬'
  }
  
  return '📄'
}

// Close autocomplete when clicking outside
const onClickOutside = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (!target.closest('.path-input-container')) {
    showAutocomplete.value = false
  }
}

onMounted(() => {
  loadDirectory(currentPath.value)
  document.addEventListener('click', onClickOutside)
})

// Watch for initialPath changes (e.g., loaded from localStorage)
watch(() => props.initialPath, (newPath) => {
  if (newPath && newPath !== currentPath.value) {
    currentPath.value = newPath
    pathInput.value = ensureTrailingSlash(newPath)
    loadDirectory(newPath)
  }
})

// Watch for input changes with debounce
let debounceTimer: number | null = null
watch(pathInput, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(() => {
    onPathInputChange()
  }, 150)
})
</script>

<template>
  <div class="space-y-4">
    <!-- Path Input Bar -->
    <div class="path-input-container relative">
      <div class="flex items-center gap-2">
        <button
          @click="goUp"
          :disabled="!listing?.parent"
          class="p-2.5 rounded-lg bg-noche-800 hover:bg-noche-700 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 transition-colors"
          title="Go up (parent directory)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        <div class="flex-1 relative">
          <input
            ref="pathInputRef"
            v-model="pathInput"
            type="text"
            class="input font-mono text-sm pr-10"
            placeholder="/path/to/directory"
            @keydown="onPathKeydown"
            @focus="onPathFocus"
            spellcheck="false"
            autocomplete="off"
          />
          <button
            @click="navigateToPath(pathInput)"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-noche-700 transition-colors"
            title="Go to path"
          >
            <svg class="w-4 h-4 text-noche-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Autocomplete Dropdown -->
      <div 
        v-if="showAutocomplete && autocompleteItems.length > 0"
        class="absolute z-50 left-12 right-0 mt-1 bg-noche-800 border border-noche-700 rounded-lg shadow-xl overflow-hidden"
      >
        <div class="text-xs text-noche-500 px-3 py-1.5 border-b border-noche-700 bg-noche-900/50">
          Tab to cycle • / or Enter to confirm • Esc to close
        </div>
        <div class="max-h-64 overflow-y-auto">
          <button
            v-for="(item, index) in autocompleteItems"
            :key="item.path"
            @click="applyAutocomplete(item)"
            class="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-noche-700 transition-colors"
            :class="{ 'bg-noche-700': index === selectedAutocompleteIndex }"
          >
            <span class="text-lg flex-shrink-0">{{ getFileIcon(item) }}</span>
            <div class="flex-1 min-w-0">
              <p class="text-noche-100 truncate font-mono text-sm">{{ item.name }}</p>
              <p class="text-xs text-noche-500 truncate">{{ item.path }}</p>
            </div>
            <span v-if="item.is_dir" class="text-xs text-noche-500 flex-shrink-0">dir</span>
            <span v-else-if="item.size" class="text-xs text-noche-500 flex-shrink-0">{{ formatSize(item.size) }}</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Quick Navigation - Full Paths -->
    <div class="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
      <button
        v-for="qp in quickPaths"
        :key="qp.path"
        @click="navigateTo(qp.path)"
        class="px-3 py-1.5 rounded-lg text-sm font-mono whitespace-nowrap transition-colors flex-shrink-0"
        :class="currentPath === qp.path || currentPath.startsWith(qp.path + '/') 
          ? 'bg-sol-500 text-noche-950' 
          : 'bg-noche-800 text-noche-400 hover:bg-noche-700 hover:text-noche-200'"
      >
        {{ qp.name }}
      </button>
    </div>

    <!-- Current Location Info -->
    <div class="flex items-center justify-between text-xs text-noche-500">
      <span>{{ listing?.files.length || 0 }} items</span>
      <span v-if="listing?.parent" class="font-mono truncate ml-2">
        ↑ {{ listing.parent }}
      </span>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center py-8">
      <div class="w-8 h-8 border-4 border-sol-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="p-4 bg-tierra-500/10 border border-tierra-500/30 rounded-xl text-center">
      <p class="text-tierra-400 mb-2">{{ error }}</p>
      <p class="text-xs text-noche-500 mb-3">Path: {{ pathInput }}</p>
      <button @click="loadDirectory(currentPath)" class="btn btn-secondary text-sm">
        Try Again
      </button>
    </div>
    
    <!-- File List -->
    <div v-else class="space-y-1 max-h-[50vh] overflow-y-auto">
      <div
        v-for="file in listing?.files || []"
        :key="file.path"
        @click="handleClick(file)"
        class="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors hover:bg-noche-800 group"
        :class="{ 'bg-noche-900/50': file.is_dir }"
      >
        <span class="text-xl flex-shrink-0">{{ getFileIcon(file) }}</span>
        
        <div class="flex-1 min-w-0">
          <p class="text-noche-100 truncate">{{ file.name }}</p>
          <p class="text-xs text-noche-600 font-mono truncate group-hover:text-noche-500">
            {{ file.path }}
          </p>
        </div>
        
        <div class="flex items-center gap-2 flex-shrink-0">
          <span v-if="!file.is_dir && file.size" class="text-xs text-noche-500">
            {{ formatSize(file.size) }}
          </span>
          <svg v-if="file.is_dir" class="w-5 h-5 text-noche-600 group-hover:text-noche-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-if="(listing?.files || []).length === 0" class="text-center py-8 text-noche-500">
        <p>No {{ props.videosOnly ? 'video ' : '' }}files found</p>
        <p class="text-xs mt-1">in {{ currentPath }}</p>
      </div>
    </div>
  </div>
</template>
