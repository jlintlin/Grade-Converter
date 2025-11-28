<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  assignments: { type: Array, required: true },
  categories: { type: Array, required: true }
})

const emit = defineEmits(['update:categories', 'add-category'])

// Track which assignments are mapped to which category
const assignmentToCategory = ref({})

// Initialize from existing category assignments
watch(() => props.categories, (cats) => {
  const mapping = {}
  cats.forEach(cat => {
    cat.assignments.forEach(a => { mapping[a] = cat.name })
  })
  assignmentToCategory.value = mapping
}, { immediate: true, deep: true })

// Unassigned assignments
const unassignedAssignments = computed(() => 
  props.assignments.filter(a => !assignmentToCategory.value[a])
)

// New category input
const newCategoryName = ref('')
const showNewCategoryInput = ref(false)

function addNewCategory() {
  if (!newCategoryName.value.trim()) return
  emit('add-category', newCategoryName.value.trim())
  newCategoryName.value = ''
  showNewCategoryInput.value = false
}

function assignToCategory(assignment, categoryName) {
  // Update local mapping
  assignmentToCategory.value[assignment] = categoryName
  
  // Update parent categories
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.name === categoryName
      ? [...new Set([...cat.assignments, assignment])]
      : cat.assignments.filter(a => a !== assignment)
  }))
  emit('update:categories', updated)
}

function removeFromCategory(assignment) {
  delete assignmentToCategory.value[assignment]
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.assignments.filter(a => a !== assignment)
  }))
  emit('update:categories', updated)
}

// Shorten assignment names for display
function shortenName(name, maxLen = 40) {
  if (name.length <= maxLen) return name
  return name.substring(0, maxLen) + '...'
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-semibold text-gray-800">Assign Columns to Categories</h2>
        <p class="text-sm text-gray-500">Drag assignments to categories or use the dropdown</p>
      </div>
      <div class="text-sm text-gray-500">
        {{ unassignedAssignments.length }} of {{ assignments.length }} unassigned
      </div>
    </div>

    <!-- Unassigned Assignments Pool -->
    <div class="mb-6 p-4 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
      <h3 class="text-sm font-medium text-gray-700 mb-3">Unassigned Assignments</h3>
      <div v-if="unassignedAssignments.length === 0" class="text-sm text-gray-400 italic">
        All assignments have been categorized
      </div>
      <div v-else class="flex flex-wrap gap-2">
        <div 
          v-for="assignment in unassignedAssignments" 
          :key="assignment"
          class="group flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition"
        >
          <span class="text-sm text-gray-700" :title="assignment">
            {{ shortenName(assignment) }}
          </span>
          <select
            @change="assignToCategory(assignment, $event.target.value); $event.target.value = ''"
            class="text-xs border border-gray-300 rounded px-2 py-1 bg-white hover:bg-gray-50"
          >
            <option value="">Assign to...</option>
            <option v-for="cat in categories" :key="cat.name" :value="cat.name">
              {{ cat.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Category Buckets -->
    <div class="space-y-4">
      <div 
        v-for="category in categories" 
        :key="category.name"
        class="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition"
      >
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-medium text-gray-800">
            {{ category.name }}
            <span class="ml-2 text-sm text-gray-500">({{ category.assignments.length }} items)</span>
          </h3>
        </div>
        <div v-if="category.assignments.length === 0" class="text-sm text-gray-400 italic py-2">
          No assignments in this category
        </div>
        <div v-else class="flex flex-wrap gap-2">
          <span 
            v-for="assignment in category.assignments" 
            :key="assignment"
            class="group flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm"
          >
            <span :title="assignment">{{ shortenName(assignment, 30) }}</span>
            <button 
              @click="removeFromCategory(assignment)"
              class="ml-1 text-blue-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
            >×</button>
          </span>
        </div>
      </div>
    </div>

    <!-- Add Category Button -->
    <div class="mt-4">
      <div v-if="showNewCategoryInput" class="flex gap-2">
        <input
          v-model="newCategoryName"
          @keyup.enter="addNewCategory"
          type="text"
          placeholder="Category name..."
          class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          autofocus
        />
        <button @click="addNewCategory" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Add</button>
        <button @click="showNewCategoryInput = false" class="px-4 py-2 text-gray-500 hover:text-gray-700">Cancel</button>
      </div>
      <button
        v-else
        @click="showNewCategoryInput = true"
        class="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-blue-400 hover:text-blue-600 transition"
      >+ Add New Category</button>
    </div>
  </div>
</template>

