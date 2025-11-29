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
  <div class="h-full w-full flex flex-col gap-4 overflow-hidden">
    <!-- Sticky Header with Controls -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 shrink-0 bg-base-100 p-4 rounded-xl border border-base-200 shadow-sm sticky top-0 z-10">
      <div class="flex items-start gap-3 flex-1">
        <div class="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold text-lg">A</div>
        <div class="space-y-1">
          <h3 class="text-xl font-bold flex items-center gap-2">
            Grading Scale
            <span v-if="extraCreditEnabled" class="badge badge-warning badge-sm gap-1">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              Extra credit to {{ maxPossibleScore }}%
            </span>
          </h3>
          <p class="text-base-content/60 text-sm">Define letter thresholds and passing cutoff before exporting.</p>
          <div class="flex items-center gap-2 text-xs text-base-content/70">
            <span class="badge badge-ghost">Editable ranges</span>
            <span class="badge badge-ghost">A+ allowed above 100%</span>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex items-center gap-2 bg-base-200 rounded-lg px-3 py-2 border border-base-300">
          <span class="text-xs font-medium text-base-content/70">Pass ≥</span>
          <input
            v-model.number="localPassingThreshold"
            type="number"
            min="0"
            max="100"
            step="1"
            :disabled="!isEditing"
            class="input input-ghost input-sm w-14 text-center font-bold p-0 focus:outline-none h-8" />
          <span class="text-xs font-bold text-base-content/50">%</span>
        </div>
        <button v-if="!isEditing" @click="startEditing" class="btn btn-primary btn-sm gap-2 shadow-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          Edit Scale
        </button>
        <template v-else>
          <button @click="resetToDefault" class="btn btn-ghost btn-sm hover:bg-base-200">Reset Default</button>
          <button @click="cancelEditing" class="btn btn-ghost btn-sm hover:bg-base-200">Cancel</button>
          <button @click="saveScale" class="btn btn-success btn-sm text-white shadow-sm gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            Save
          </button>
        </template>
      </div>
    </div>

    <!-- Main Content Area - Two Columns without vertical scroll -->
    <div class="grid gap-4 lg:grid-cols-2 auto-rows-min">
       <!-- Passing Grades Column -->
       <div class="flex flex-col bg-base-100 border border-base-200 rounded-xl shadow-sm">
          <div class="px-4 py-3 border-b border-base-200 bg-success/5 flex items-center justify-between">
             <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-success"></div>
                <h4 class="font-bold text-sm uppercase tracking-wider text-success">Passing Grades</h4>
             </div>
             <div class="text-xs text-base-content/60">Pass threshold: {{ localPassingThreshold }}%</div>
          </div>
          <table class="table table-sm w-full">
            <thead class="bg-base-100 shadow-sm">
              <tr class="text-xs text-base-content/50">
                <th class="pl-4">Grade</th>
                <th>Min %</th>
                <th>Range</th>
                <th v-if="isEditing" class="w-10"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in passingGrades" :key="item.grade" class="hover:bg-base-50 transition-colors border-b border-base-100 last:border-0">
                <td class="pl-4">
                   <div class="font-bold w-7 h-7 rounded-md flex items-center justify-center text-sm" :class="getGradeBgClass(item.grade)">
                      <span :class="getGradeColorClass(item.grade)">{{ item.grade }}</span>
                   </div>
                </td>
                <td class="font-mono">
                  <div v-if="isEditing" class="flex items-center gap-1">
                    <span class="text-base-content/40 text-[10px] font-bold">≥</span>
                    <input
                        type="number"
                        :value="item.threshold"
                        @input="updateThreshold(item.grade, $event.target.value)"
                        class="input input-bordered input-xs w-12 text-right px-1 font-bold focus:input-primary"
                        min="0" max="110" step="0.5" />
                  </div>
                  <span v-else class="font-bold text-base-content/80 text-sm">≥ {{ item.threshold }}%</span>
                </td>
                <td class="text-xs text-base-content/60 font-medium">{{ getGradeRange(item.threshold, sortedGrades.findIndex(g => g.grade === item.grade)) }}</td>
                <td v-if="isEditing" class="text-right pr-2">
                  <button @click="removeGrade(item.grade)" class="btn btn-ghost btn-xs btn-square text-error/70 hover:text-error hover:bg-error/10">
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
       </div>

       <!-- Failing Grades & Add New -->
       <div class="flex flex-col gap-4">
          <!-- Failing Grades -->
          <div class="flex flex-col bg-base-100 border border-base-200 rounded-xl shadow-sm">
             <div class="px-4 py-3 border-b border-base-200 bg-error/5 flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-error"></div>
                <h4 class="font-bold text-sm uppercase tracking-wider text-error">Failing Grades</h4>
             </div>
             <table class="table table-sm w-full">
               <thead class="bg-base-100 shadow-sm">
                 <tr class="text-xs text-base-content/50">
                   <th class="pl-4">Grade</th>
                   <th>Min %</th>
                   <th>Range</th>
                   <th v-if="isEditing" class="w-10"></th>
                 </tr>
               </thead>
               <tbody>
                 <tr v-for="(item, idx) in failingGrades" :key="item.grade" class="hover:bg-base-50 transition-colors border-b border-base-100 last:border-0">
                   <td class="pl-4">
                      <div class="font-bold w-7 h-7 rounded-md flex items-center justify-center text-sm" :class="getGradeBgClass(item.grade)">
                         <span :class="getGradeColorClass(item.grade)">{{ item.grade }}</span>
                      </div>
                   </td>
                   <td class="font-mono">
                     <div v-if="isEditing" class="flex items-center gap-1">
                       <span class="text-base-content/40 text-[10px] font-bold">≥</span>
                       <input
                           type="number"
                           :value="item.threshold"
                           @input="updateThreshold(item.grade, $event.target.value)"
                           class="input input-bordered input-xs w-12 text-right px-1 font-bold focus:input-primary"
                           min="0" max="110" step="0.5" />
                     </div>
                     <span v-else class="font-bold text-base-content/80 text-sm">≥ {{ item.threshold }}%</span>
                   </td>
                   <td class="text-xs text-base-content/60 font-medium">{{ getGradeRange(item.threshold, sortedGrades.findIndex(g => g.grade === item.grade)) }}</td>
                   <td v-if="isEditing" class="text-right pr-2">
                     <button v-if="item.grade !== 'F'" @click="removeGrade(item.grade)" class="btn btn-ghost btn-xs btn-square text-error/70 hover:text-error hover:bg-error/10">
                       <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                     </button>
                   </td>
                 </tr>
               </tbody>
             </table>
          </div>

          <!-- Add New Grade (Edit Mode Only) -->
          <div v-if="isEditing" class="bg-base-100 border-2 border-dashed border-base-300 rounded-xl p-4 flex flex-col gap-3">
             <div class="flex items-center gap-2 text-primary font-bold text-sm">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Add Custom Grade
             </div>
             <div class="flex items-center gap-2">
                <input v-model="newGrade" placeholder="Grade (e.g. A+)" class="input input-bordered input-sm w-full focus:input-primary" />
                <div class="flex items-center bg-base-50 px-2 py-1 rounded-lg border border-base-200 shrink-0">
                  <span class="text-base-content/40 font-bold text-xs mr-1">≥</span>
                  <input v-model.number="newThreshold" type="number" placeholder="97" class="input input-ghost input-sm w-12 text-center font-bold p-0 focus:outline-none h-8" min="0" max="110" />
                  <span class="text-base-content/40 font-bold text-xs ml-1">%</span>
                </div>
                <button @click="addGrade" class="btn btn-sm btn-primary" :disabled="!newGrade.trim()">Add</button>
             </div>
          </div>
       </div>
    </div>
  </div>
</template>

<style scoped>
/* Enhanced grade styling */
</style>
