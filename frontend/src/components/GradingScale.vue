<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  passingThreshold: { type: Number, default: 60 },
  extraCreditEnabled: { type: Boolean, default: false },
  maxExtraCreditPercent: { type: Number, default: 5 }
})

const emit = defineEmits(['update:modelValue', 'update:passingThreshold'])

const isEditing = ref(false)
const localScale = ref({})
const newGrade = ref('')
const newThreshold = ref(0)
const localPassingThreshold = ref(props.passingThreshold)

// Sync passing threshold with props
watch(() => props.passingThreshold, (val) => {
  localPassingThreshold.value = val
})

// Standard grading scale with support for A+ above 100%
const defaultScale = {
  'A+': 97.0, 'A': 93.0, 'A-': 90.0,
  'B+': 87.0, 'B': 83.0, 'B-': 80.0,
  'C+': 77.0, 'C': 73.0, 'C-': 70.0,
  'D+': 67.0, 'D': 63.0, 'D-': 60.0,
  'F': 0.0
}

onMounted(async () => {
  if (Object.keys(props.modelValue).length === 0) {
    try {
      const response = await axios.get('/api/grading-scale/default')
      localScale.value = { ...response.data.scale }
      emit('update:modelValue', localScale.value)
    } catch (e) {
      localScale.value = { ...defaultScale }
      emit('update:modelValue', localScale.value)
    }
  } else {
    localScale.value = { ...props.modelValue }
  }
})

const sortedGrades = computed(() => {
  return Object.entries(localScale.value)
    .sort((a, b) => b[1] - a[1])
    .map(([grade, threshold]) => ({ grade, threshold }))
})

// Separate passing and failing grades for two-column layout
const passingGrades = computed(() => {
  return sortedGrades.value.filter(item => item.threshold >= localPassingThreshold.value)
})

const failingGrades = computed(() => {
  return sortedGrades.value.filter(item => item.threshold < localPassingThreshold.value)
})

// Maximum possible score based on extra credit
const maxPossibleScore = computed(() => {
  return props.extraCreditEnabled ? 100 + props.maxExtraCreditPercent : 100
})

function startEditing() { isEditing.value = true }

function saveScale() {
  emit('update:modelValue', { ...localScale.value })
  emit('update:passingThreshold', localPassingThreshold.value)
  isEditing.value = false
}

function cancelEditing() {
  localScale.value = { ...props.modelValue }
  localPassingThreshold.value = props.passingThreshold
  isEditing.value = false
}

function updateThreshold(grade, value) {
  localScale.value[grade] = parseFloat(value) || 0
}

function removeGrade(grade) {
  if (grade !== 'F') {
    delete localScale.value[grade]
  }
}

function addGrade() {
  if (newGrade.value && !localScale.value[newGrade.value]) {
    localScale.value[newGrade.value] = parseFloat(newThreshold.value) || 0
    newGrade.value = ''
    newThreshold.value = 0
  }
}

function resetToDefault() {
  localScale.value = { ...defaultScale }
  localPassingThreshold.value = 60
}

function getGradeRange(threshold, index) {
  if (index === 0) {
    // First grade (highest) - show max possible including extra credit
    return `≥${threshold}% (up to ${maxPossibleScore.value}%)`
  }
  const prevThreshold = sortedGrades.value[index - 1].threshold
  return `${threshold}% – ${(prevThreshold - 0.1).toFixed(1)}%`
}

function getGradeColorClass(grade) {
  if (grade.startsWith('A')) return 'text-success'
  if (grade.startsWith('B')) return 'text-info'
  if (grade.startsWith('C')) return 'text-warning'
  if (grade.startsWith('D')) return 'text-orange-500'
  return 'text-error'
}

function getGradeBgClass(grade) {
  if (grade.startsWith('A')) return 'bg-success/10 border-success/30'
  if (grade.startsWith('B')) return 'bg-info/10 border-info/30'
  if (grade.startsWith('C')) return 'bg-warning/10 border-warning/30'
  if (grade.startsWith('D')) return 'bg-orange-500/10 border-orange-500/30'
  return 'bg-error/10 border-error/30'
}

function isPassingGrade(threshold) {
  return threshold >= localPassingThreshold.value
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header with Help Text -->
    <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
      <div class="flex-1">
        <h3 class="text-lg font-bold flex items-center gap-2">
          📏 Grading Scale Configuration
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-xs btn-circle">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div tabindex="0" class="dropdown-content z-50 card card-compact w-72 p-2 shadow bg-base-100 border border-base-300">
              <div class="card-body">
                <h4 class="font-bold text-sm">How Grading Scale Works</h4>
                <ul class="text-xs space-y-1 text-base-content/80">
                  <li>• Each letter grade has a <strong>minimum percentage threshold</strong></li>
                  <li>• Students scoring ≥ threshold receive that letter grade</li>
                  <li>• Click "Edit Scale" to customize thresholds</li>
                  <li>• When extra credit is enabled, grades can exceed 100%</li>
                  <li>• The passing threshold determines pass/fail statistics</li>
                </ul>
              </div>
            </div>
          </div>
        </h3>
        <p class="text-base-content/60 text-sm mt-1">
          Define minimum percentage thresholds for each letter grade.
          <span v-if="extraCreditEnabled" class="text-warning">Extra credit enabled: max score {{ maxPossibleScore }}%</span>
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-2 flex-shrink-0">
        <button v-if="!isEditing" @click="startEditing" class="btn btn-sm btn-primary gap-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          Edit Scale
        </button>
        <template v-else>
          <button @click="resetToDefault" class="btn btn-sm btn-ghost">Reset Default</button>
          <button @click="cancelEditing" class="btn btn-sm btn-ghost">Cancel</button>
          <button @click="saveScale" class="btn btn-sm btn-success">Save Changes</button>
        </template>
      </div>
    </div>

    <!-- Passing Threshold Setting -->
    <div class="bg-base-200 rounded-lg p-4 space-y-3">
      <div class="flex flex-col sm:flex-row sm:items-center gap-4">
        <div class="flex-1">
          <label class="label py-0">
            <span class="label-text font-semibold">Passing Grade Threshold</span>
          </label>
          <p class="text-xs text-base-content/60 mt-1">
            Students scoring below this percentage will be marked as "Failing" in the results summary.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model.number="localPassingThreshold"
            type="range"
            min="0"
            max="100"
            step="1"
            class="range range-xs w-40"
            :disabled="!isEditing" />
          <input
            v-model.number="localPassingThreshold"
            type="number"
            min="0"
            max="100"
            step="1"
            :disabled="!isEditing"
            class="input input-bordered input-sm w-20 text-center"
            :class="{ 'input-disabled': !isEditing }" />
          <span class="text-sm font-medium">%</span>
        </div>
      </div>
      <div v-if="!isEditing" class="text-xs text-base-content/60">Click "Edit Scale" to change passing threshold.</div>
    </div>

    <!-- Grade Scale Table -->
    <div class="bg-base-100 border border-base-300 rounded-xl shadow-sm overflow-hidden">
      <div class="px-4 py-3 border-b border-base-300 flex items-center justify-between">
        <h4 class="font-semibold">Letter thresholds</h4>
        <span class="text-xs text-base-content/60">Max score {{ maxPossibleScore }}%</span>
      </div>
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Grade</th>
              <th>Min %</th>
              <th>Range</th>
              <th>Status</th>
              <th class="w-16 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in sortedGrades" :key="item.grade" class="hover">
              <td class="font-bold" :class="getGradeColorClass(item.grade)">{{ item.grade }}</td>
              <td class="font-mono">
                <div v-if="isEditing" class="flex items-center gap-1">
                  <span class="text-base-content/50 text-xs">≥</span>
                  <input
                    type="number"
                    :value="item.threshold"
                    @input="updateThreshold(item.grade, $event.target.value)"
                    class="input input-bordered input-xs w-20"
                    min="0"
                    max="110"
                    step="0.5" />
                  <span class="text-base-content/50 text-xs">%</span>
                </div>
                <span v-else class="font-mono">{{ item.threshold }}%</span>
              </td>
              <td class="text-xs text-base-content/70">{{ getGradeRange(item.threshold, idx) }}</td>
              <td>
                <span :class="['badge badge-xs', isPassingGrade(item.threshold) ? 'badge-success' : 'badge-error']">
                  {{ isPassingGrade(item.threshold) ? 'Pass' : 'Fail' }}
                </span>
              </td>
              <td class="text-right">
                <button
                  v-if="isEditing && item.grade !== 'F'"
                  @click="removeGrade(item.grade)"
                  class="btn btn-ghost btn-xs text-error">
                  ×
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add New Grade (Edit Mode) -->
    <div v-if="isEditing" class="flex flex-wrap items-center gap-3 p-4 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
      <span class="text-sm font-medium">Add Custom Grade:</span>
      <input
        v-model="newGrade"
        placeholder="e.g., A+"
        class="input input-bordered input-sm w-24" />
      <div class="flex items-center gap-1">
        <span class="text-base-content/60">≥</span>
        <input
          v-model.number="newThreshold"
          type="number"
          placeholder="97"
          class="input input-bordered input-sm w-20"
          min="0"
          max="110" />
        <span class="text-base-content/60">%</span>
      </div>
      <button @click="addGrade" class="btn btn-sm btn-primary gap-1" :disabled="!newGrade.trim()">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Grade
      </button>
    </div>

    <!-- Info Alert -->
    <div v-if="extraCreditEnabled" class="alert alert-warning">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>
        <strong>Extra Credit Enabled:</strong> Students can earn up to {{ maxPossibleScore }}% total.
        The highest grade ({{ sortedGrades[0]?.grade || 'A+' }}) will apply to scores from {{ sortedGrades[0]?.threshold }}% to {{ maxPossibleScore }}%.
      </span>
    </div>
  </div>
</template>

<style scoped>
/* Enhanced grade styling */
</style>
