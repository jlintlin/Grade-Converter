<script setup>
import { computed } from 'vue'

const props = defineProps({
  categories: {
    type: Array,
    required: true
  },
  totalWeight: {
    type: Number,
    default: 0
  },
  isValid: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:categories', 'calculate'])

// Update a specific category
function updateCategory(index, field, value) {
  const updated = [...props.categories]
  updated[index] = { ...updated[index], [field]: value }
  emit('update:categories', updated)
}

// Remove a category
function removeCategory(index) {
  const updated = props.categories.filter((_, i) => i !== index)
  emit('update:categories', updated)
}

// Weight validation styling
const weightStatus = computed(() => {
  const total = props.totalWeight
  if (Math.abs(total - 100) < 0.01) return 'valid'
  if (total < 100) return 'under'
  return 'over'
})

// Check if any category has assignments
const hasAssignments = computed(() =>
  props.categories.some(cat => cat.assignments.length > 0)
)

// Can calculate (valid weights and has assignments)
const canCalculate = computed(() => props.isValid && hasAssignments.value)
</script>

<template>
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="card-title text-2xl">⚖️ Category Weights</h2>
          <p class="text-base-content/60 mt-1">Configure the weight for each grading category</p>
        </div>

        <!-- Weight Total Indicator -->
        <div :class="[
          'badge badge-lg gap-2 p-4',
          weightStatus === 'valid' ? 'badge-success' :
          weightStatus === 'under' ? 'badge-warning' :
          'badge-error'
        ]">
          <span class="font-bold">{{ totalWeight.toFixed(1) }}%</span>
          <span v-if="weightStatus === 'valid'">✓</span>
          <span v-else-if="weightStatus === 'under'">({{ (100 - totalWeight).toFixed(1) }}% left)</span>
          <span v-else>({{ (totalWeight - 100).toFixed(1) }}% over)</span>
        </div>
      </div>

      <!-- Categories List -->
      <div class="space-y-4">
        <div v-for="(category, index) in categories" :key="index"
             class="card bg-base-200 border border-base-300 hover:border-primary transition-colors">
          <div class="card-body p-4">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
              <!-- Category Name -->
              <div class="md:col-span-4">
                <label class="label"><span class="label-text font-medium">Category Name</span></label>
                <input :value="category.name"
                       @input="updateCategory(index, 'name', $event.target.value)"
                       type="text" class="input input-bordered w-full" />
              </div>

              <!-- Weight -->
              <div class="md:col-span-2">
                <label class="label"><span class="label-text font-medium">Weight %</span></label>
                <input :value="category.weight"
                       @input="updateCategory(index, 'weight', parseFloat($event.target.value) || 0)"
                       type="number" min="0" max="100" step="0.5"
                       class="input input-bordered w-full" />
              </div>

              <!-- Drop Lowest -->
              <div class="md:col-span-2">
                <label class="label"><span class="label-text font-medium">Drop Lowest</span></label>
                <input :value="category.drop_lowest"
                       @input="updateCategory(index, 'drop_lowest', parseInt($event.target.value) || 0)"
                       type="number" min="0"
                       class="input input-bordered w-full" />
              </div>

              <!-- Assignments Count -->
              <div class="md:col-span-3">
                <label class="label"><span class="label-text font-medium">Assignments</span></label>
                <div class="badge badge-lg badge-outline w-full justify-start py-4">
                  📝 {{ category.assignments.length }} assignment(s)
                </div>
              </div>

              <!-- Remove Button -->
              <div class="md:col-span-1 flex items-end justify-end">
                <button @click="removeCategory(index)" class="btn btn-ghost btn-sm text-error"
                        title="Remove category">
                  <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Assignment Pills -->
            <div v-if="category.assignments.length > 0" class="mt-3 flex flex-wrap gap-1.5">
              <span v-for="assignment in category.assignments.slice(0, 5)" :key="assignment"
                    class="badge badge-sm badge-ghost" :title="assignment">
                {{ assignment.length > 25 ? assignment.substring(0, 25) + '...' : assignment }}
              </span>
              <span v-if="category.assignments.length > 5" class="badge badge-sm badge-neutral">
                +{{ category.assignments.length - 5 }} more
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Validation Messages -->
      <div v-if="categories.length > 0" class="mt-4 space-y-2">
        <div v-if="!hasAssignments" role="alert" class="alert alert-warning">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>No assignments mapped. Go back to "Assign Categories" to map assignments.</span>
        </div>
        <div v-if="!isValid && hasAssignments" role="alert" class="alert alert-warning">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Category weights must sum to exactly 100% before calculating grades.</span>
        </div>
      </div>
    </div>
  </div>
</template>

