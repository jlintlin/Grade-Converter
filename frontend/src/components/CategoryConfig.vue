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
  <div class="bg-white rounded-xl shadow-lg p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-semibold text-gray-800">Grade Category Configuration</h2>
        <p class="text-sm text-gray-500">Configure weights for each category</p>
      </div>
      
      <!-- Weight Total Indicator -->
      <div 
        :class="[
          'px-4 py-2 rounded-lg font-medium',
          weightStatus === 'valid' ? 'bg-green-100 text-green-800' :
          weightStatus === 'under' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        ]"
      >
        Total: {{ totalWeight.toFixed(1) }}%
        <span v-if="weightStatus === 'valid'" class="ml-1">✓</span>
        <span v-else-if="weightStatus === 'under'" class="ml-1">({{ (100 - totalWeight).toFixed(1) }}% remaining)</span>
        <span v-else class="ml-1">({{ (totalWeight - 100).toFixed(1) }}% over)</span>
      </div>
    </div>

    <!-- Categories List -->
    <div class="space-y-4">
      <div 
        v-for="(category, index) in categories" 
        :key="index"
        class="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition"
      >
        <div class="grid grid-cols-12 gap-4 items-start">
          <!-- Category Name -->
          <div class="col-span-3">
            <label class="block text-sm font-medium text-gray-700 mb-1">Category Name</label>
            <input
              :value="category.name"
              @input="updateCategory(index, 'name', $event.target.value)"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <!-- Weight -->
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Weight %</label>
            <input
              :value="category.weight"
              @input="updateCategory(index, 'weight', parseFloat($event.target.value) || 0)"
              type="number"
              min="0"
              max="100"
              step="0.5"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <!-- Drop Lowest -->
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Drop Lowest</label>
            <input
              :value="category.drop_lowest"
              @input="updateCategory(index, 'drop_lowest', parseInt($event.target.value) || 0)"
              type="number"
              min="0"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <!-- Assignments Count -->
          <div class="col-span-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">Assignments</label>
            <div class="px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-600">
              {{ category.assignments.length }} assignment(s)
            </div>
          </div>
          
          <!-- Remove Button -->
          <div class="col-span-1 flex items-end">
            <button
              @click="removeCategory(index)"
              class="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
              title="Remove category"
            >
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
        
        <!-- Assignment Pills -->
        <div v-if="category.assignments.length > 0" class="mt-3 flex flex-wrap gap-2">
          <span 
            v-for="assignment in category.assignments.slice(0, 5)" 
            :key="assignment"
            class="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
            :title="assignment"
          >
            {{ assignment.length > 25 ? assignment.substring(0, 25) + '...' : assignment }}
          </span>
          <span 
            v-if="category.assignments.length > 5"
            class="px-2 py-1 bg-gray-200 text-gray-600 rounded text-xs"
          >
            +{{ category.assignments.length - 5 }} more
          </span>
        </div>
      </div>
    </div>

    <!-- Validation Messages -->
    <div v-if="categories.length > 0" class="mt-4 space-y-2">
      <div v-if="!hasAssignments" class="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
        ⚠️ No assignments are mapped to categories. Go to "Assign Categories" tab to map assignments.
      </div>
      <div v-if="!isValid && hasAssignments" class="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
        ⚠️ Category weights must sum to exactly 100% before calculating grades.
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="mt-6 flex justify-end gap-4">
      <button
        @click="emit('calculate')"
        :disabled="!canCalculate"
        :class="[
          'px-6 py-2 rounded-lg font-medium transition',
          canCalculate
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        ]"
      >
        Calculate Grades
      </button>
    </div>
  </div>
</template>

