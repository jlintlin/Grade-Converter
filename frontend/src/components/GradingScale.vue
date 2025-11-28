<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue'])

const isEditing = ref(false)
const localScale = ref({})
const newGrade = ref('')
const newThreshold = ref(0)

// Standard grading scale (matching backend)
const defaultScale = {
  'A': 90.0, 'A-': 87.0, 'B+': 84.0, 'B': 80.0, 'B-': 77.0,
  'C+': 74.0, 'C': 70.0, 'C-': 67.0, 'D+': 64.0, 'D': 61.0,
  'D-': 57.0, 'F': 0.0
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

function startEditing() { isEditing.value = true }

function saveScale() {
  emit('update:modelValue', { ...localScale.value })
  isEditing.value = false
}

function cancelEditing() {
  localScale.value = { ...props.modelValue }
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
}

function getGradeRange(threshold, index) {
  if (index === 0) return `${threshold}% - 100%`
  const prevThreshold = sortedGrades.value[index - 1].threshold
  return `${threshold}% - ${prevThreshold - 1}%`
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold text-gray-800">Grading Scale</h2>
      <div class="flex gap-2">
        <button v-if="!isEditing" @click="startEditing" class="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200">
          Edit Scale
        </button>
        <template v-else>
          <button @click="resetToDefault" class="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">Reset</button>
          <button @click="cancelEditing" class="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">Cancel</button>
          <button @click="saveScale" class="px-3 py-1 text-sm bg-green-500 text-white rounded-lg hover:bg-green-600">Save</button>
        </template>
      </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
      <div v-for="(item, idx) in sortedGrades" :key="item.grade" 
           class="flex items-center justify-between p-2 rounded-lg"
           :class="isEditing ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'">
        <span class="font-semibold text-gray-800 w-8">{{ item.grade }}</span>
        <template v-if="isEditing">
          <input type="number" :value="item.threshold" @input="updateThreshold(item.grade, $event.target.value)"
                 class="w-16 px-2 py-1 text-sm border rounded" min="0" max="100" step="1" />
          <button v-if="item.grade !== 'F'" @click="removeGrade(item.grade)" class="text-red-500 hover:text-red-700 ml-1">×</button>
        </template>
        <span v-else class="text-sm text-gray-600">{{ getGradeRange(item.threshold, idx) }}</span>
      </div>
    </div>

    <div v-if="isEditing" class="mt-4 flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
      <input v-model="newGrade" placeholder="Grade (e.g., A+)" class="w-24 px-2 py-1 text-sm border rounded" />
      <input v-model.number="newThreshold" type="number" placeholder="Min %" class="w-20 px-2 py-1 text-sm border rounded" min="0" max="100" />
      <button @click="addGrade" class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">Add</button>
    </div>
  </div>
</template>

