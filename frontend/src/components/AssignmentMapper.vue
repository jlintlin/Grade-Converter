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

function assignAllTo(categoryName) {
  // Assign all unassigned to the selected category
  unassignedAssignments.value.forEach(assignment => {
    assignmentToCategory.value[assignment] = categoryName
  })
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.name === categoryName
      ? [...new Set([...cat.assignments, ...unassignedAssignments.value])]
      : cat.assignments
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
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="card-title text-2xl">🏷️ Assign Categories</h2>
          <p class="text-base-content/60 mt-1">Assign each assignment to a grading category</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="badge badge-lg" :class="unassignedAssignments.length === 0 ? 'badge-success' : 'badge-warning'">
            {{ assignments.length - unassignedAssignments.length }}/{{ assignments.length }} assigned
          </span>
        </div>
      </div>

      <!-- Unassigned Assignments Pool -->
      <div class="bg-base-200 rounded-box p-4 mb-6 border-2 border-dashed border-base-300">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold flex items-center gap-2">
            <span class="badge badge-neutral">{{ unassignedAssignments.length }}</span>
            Unassigned Assignments
          </h3>
          <!-- Batch assign dropdown -->
          <div v-if="unassignedAssignments.length > 0" class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-sm btn-primary gap-1">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Assign All
            </div>
            <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-lg bg-base-100 rounded-box w-52">
              <li v-for="cat in categories" :key="cat.name">
                <a @click="assignAllTo(cat.name)">{{ cat.name }}</a>
              </li>
            </ul>
          </div>
        </div>

        <div v-if="unassignedAssignments.length === 0" class="alert alert-success">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>All assignments have been categorized!</span>
        </div>
        <div v-else class="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
          <div v-for="assignment in unassignedAssignments" :key="assignment"
               class="flex items-center gap-2 px-3 py-2 bg-base-100 rounded-lg shadow-sm border border-base-300">
            <span class="text-sm" :title="assignment">{{ shortenName(assignment) }}</span>
            <select @change="assignToCategory(assignment, $event.target.value); $event.target.value = ''"
                    class="select select-bordered select-xs w-28">
              <option value="">Assign...</option>
              <option v-for="cat in categories" :key="cat.name" :value="cat.name">{{ cat.name }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Category Buckets Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="category in categories" :key="category.name"
             class="card bg-base-200 border border-base-300 hover:border-primary transition-colors">
          <div class="card-body p-4">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-lg flex items-center gap-2">
                {{ category.name }}
                <span class="badge badge-sm badge-primary">{{ category.assignments.length }}</span>
              </h3>
            </div>

            <div v-if="category.assignments.length === 0" class="text-base-content/50 text-sm italic py-4 text-center">
              Drop assignments here
            </div>
            <div v-else class="flex flex-wrap gap-1.5 mt-2 max-h-32 overflow-y-auto">
              <span v-for="assignment in category.assignments" :key="assignment"
                    class="badge badge-outline gap-1 cursor-default group">
                <span :title="assignment">{{ shortenName(assignment, 25) }}</span>
                <button @click="removeFromCategory(assignment)"
                        class="opacity-0 group-hover:opacity-100 hover:text-error transition">×</button>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Add Category -->
      <div class="mt-4">
        <div v-if="showNewCategoryInput" class="flex gap-2">
          <input v-model="newCategoryName" @keyup.enter="addNewCategory" type="text"
                 placeholder="Category name..." class="input input-bordered flex-1" autofocus />
          <button @click="addNewCategory" class="btn btn-primary">Add</button>
          <button @click="showNewCategoryInput = false" class="btn btn-ghost">Cancel</button>
        </div>
        <button v-else @click="showNewCategoryInput = true"
                class="btn btn-outline btn-block border-2 border-dashed">
          + Add New Category
        </button>
      </div>
    </div>
  </div>
</template>

