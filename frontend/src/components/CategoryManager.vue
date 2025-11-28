<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  assignments: { type: Array, required: true },
  assignmentInfo: { type: Object, default: () => ({}) },
  categories: { type: Array, required: true },
  extraCreditEnabled: { type: Boolean, default: false },
  maxExtraCreditPercent: { type: Number, default: 5 },
  replacementRules: { type: Object, default: () => ({}) },
  replacementEnabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:categories', 'update:extraCreditEnabled', 'update:maxExtraCreditPercent', 'update:replacementRules', 'update:replacementEnabled'])

// Drag state
const draggedAssignment = ref(null)
const dragOverCategory = ref(null)

// New category modal
const showNewCategoryModal = ref(false)
const newCategoryName = ref('')
const newCategoryWeight = ref(10)
const selectedAssignments = ref(new Set())

// Replacement assignment modal (legacy - keeping for context menu)
const showReplacementModal = ref(false)
const selectedReplacementAssignment = ref(null)
const replacementTargetCategory = ref('')

// New replacement rule form
const newReplacementAssignment = ref('')
const newReplacementTargets = ref([]) // Changed to array for multi-select

// Track replacement assignments - maps assignment name to array of target assignments
// Initialize from props
const replacementAssignments = ref({ ...props.replacementRules })

// Flag to prevent circular updates between watchers
let isUpdatingFromProps = false

// Watch for prop changes to sync local state
watch(() => props.replacementRules, (newRules) => {
  // Only update if the change came from outside (not from our own emit)
  const newKeys = Object.keys(newRules).sort().join(',')
  const currentKeys = Object.keys(replacementAssignments.value).sort().join(',')
  if (newKeys !== currentKeys) {
    isUpdatingFromProps = true
    replacementAssignments.value = { ...newRules }
    isUpdatingFromProps = false
  }
}, { deep: true })

// Watch for local changes to emit to parent
watch(replacementAssignments, (newRules) => {
  // Only emit if the change was local (not from props)
  if (!isUpdatingFromProps) {
    emit('update:replacementRules', { ...newRules })
  }
}, { deep: true })

// Extra credit assignments (separate from category extra credit)
const extraCreditAssignments = ref(new Set())

// Extra Credit Category Name (constant)
const EXTRA_CREDIT_CATEGORY = 'Extra Credit'

// Watch for extra credit toggle to auto-create/remove category
watch(() => props.extraCreditEnabled, (enabled) => {
  const hasExtraCreditCategory = props.categories.some(c => c.name === EXTRA_CREDIT_CATEGORY)

  if (enabled && !hasExtraCreditCategory) {
    // Auto-create Extra Credit category with 0% weight (doesn't count toward 100%)
    const updated = [...props.categories, {
      name: EXTRA_CREDIT_CATEGORY,
      weight: 0,
      drop_lowest: 0,
      assignments: [],
      extra_credit: true
    }]
    emit('update:categories', updated)
  } else if (!enabled && hasExtraCreditCategory) {
    // Remove Extra Credit category when disabled
    const updated = props.categories.filter(c => c.name !== EXTRA_CREDIT_CATEGORY)
    emit('update:categories', updated)
  }
})

// Track assignment to category mapping
const assignmentToCategory = computed(() => {
  const mapping = {}
  props.categories.forEach(cat => {
    cat.assignments.forEach(a => { mapping[a] = cat.name })
  })
  return mapping
})

// Unassigned assignments
const unassignedAssignments = computed(() =>
  props.assignments.filter(a => !assignmentToCategory.value[a])
)

// Available assignments for replacement (unassigned ones that aren't already replacers)
const availableReplacerAssignments = computed(() =>
  unassignedAssignments.value.filter(a => !replacementAssignments.value[a])
)

// Categories that are not Extra Credit (valid targets for replacement)
const nonExtraCreditCategories = computed(() =>
  props.categories.filter(c => c.name !== EXTRA_CREDIT_CATEGORY)
)

// Assigned assignments that can be targets for replacement (not in Extra Credit category)
const availableTargetAssignments = computed(() => {
  const targets = []
  for (const cat of nonExtraCreditCategories.value) {
    for (const a of cat.assignments) {
      targets.push({ name: a, category: cat.name })
    }
  }
  return targets
})

// Total weight validation (excluding Extra Credit category which is bonus-only)
const totalWeight = computed(() =>
  props.categories
    .filter(c => !c.extra_credit)
    .reduce((sum, c) => sum + (c.weight || 0), 0)
)
const remainingWeight = computed(() => 100 - totalWeight.value)
const isWeightValid = computed(() => Math.abs(totalWeight.value - 100) < 0.01)
const isWeightOver = computed(() => totalWeight.value > 100)
const selectedCount = computed(() => selectedAssignments.value.size)

// Helper: clean assignment name - remove Canvas IDs and technical details
function cleanAssignmentName(name) {
  let cleaned = name
  // Remove Canvas assignment IDs like (12345) or (9145575)
  cleaned = cleaned.replace(/\s*\(\d+\)\s*$/g, '')
  // Remove "- Requires Respondus LockDown Browser" and similar
  cleaned = cleaned.replace(/[-–]\s*Requires\s+Respondus.*$/i, '')
  // Remove "(Required)" suffix but keep other meaningful parenthetical
  cleaned = cleaned.replace(/\s*\(Required\)\s*/gi, ' ')
  // Remove extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  return cleaned
}

// Helper: shorten assignment names for display
function shortenName(name, maxLen = 30) {
  const cleaned = cleanAssignmentName(name)
  if (cleaned.length <= maxLen) return cleaned
  return cleaned.substring(0, maxLen) + '...'
}

// Get full original name for tooltips
function getOriginalName(name) {
  return name
}

// Get Canvas ID from assignment name
function getCanvasId(name) {
  const match = name.match(/\((\d+)\)\s*$/)
  return match ? match[1] : null
}

// Get points possible for an assignment
function getPointsPossible(name) {
  return props.assignmentInfo[name]?.points_possible
}

// Drag handlers
function onDragStart(assignment, event) {
  draggedAssignment.value = assignment
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', assignment)
}

function onDragEnd() {
  draggedAssignment.value = null
  dragOverCategory.value = null
}

function onDragOver(categoryName, event) {
  event.preventDefault()
  dragOverCategory.value = categoryName
}

function onDragLeave() {
  dragOverCategory.value = null
}

function onDrop(categoryName, event) {
  event.preventDefault()
  const assignment = draggedAssignment.value
  if (!assignment) return
  
  assignToCategory(assignment, categoryName)
  draggedAssignment.value = null
  dragOverCategory.value = null
}

// Assignment management
function assignToCategory(assignment, categoryName) {
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.name === categoryName
      ? [...new Set([...cat.assignments, assignment])]
      : cat.assignments.filter(a => a !== assignment)
  }))
  emit('update:categories', updated)
}

function removeFromCategory(assignment) {
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.assignments.filter(a => a !== assignment)
  }))
  emit('update:categories', updated)
}

function assignAllTo(categoryName) {
  const toAssign = [...unassignedAssignments.value]
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.name === categoryName
      ? [...new Set([...cat.assignments, ...toAssign])]
      : cat.assignments
  }))
  emit('update:categories', updated)
}

// Category management
function addCategory() {
  if (!newCategoryName.value.trim()) return
  const updated = [...props.categories, {
    name: newCategoryName.value.trim(),
    weight: newCategoryWeight.value,
    drop_lowest: 0,
    assignments: [],
    extra_credit: false
  }]
  emit('update:categories', updated)
  newCategoryName.value = ''
  newCategoryWeight.value = 10
  showNewCategoryModal.value = false
}

function updateCategory(index, field, value) {
  const updated = [...props.categories]
  updated[index] = { ...updated[index], [field]: value }
  emit('update:categories', updated)
}

function removeCategory(index) {
  const updated = props.categories.filter((_, i) => i !== index)
  emit('update:categories', updated)
}

// Replacement assignment functions
function openReplacementModal(assignment) {
  selectedReplacementAssignment.value = assignment
  replacementTargetCategory.value = ''
  showReplacementModal.value = true
}

function setReplacementAssignment() {
  if (!selectedReplacementAssignment.value || !replacementTargetCategory.value) return
  replacementAssignments.value[selectedReplacementAssignment.value] = replacementTargetCategory.value
  showReplacementModal.value = false
}

function addReplacementRule() {
  if (!newReplacementAssignment.value || newReplacementTargets.value.length === 0) return
  replacementAssignments.value[newReplacementAssignment.value] = [...newReplacementTargets.value]
  // Reset form
  newReplacementAssignment.value = ''
  newReplacementTargets.value = []
}

function clearReplacement(assignment) {
  delete replacementAssignments.value[assignment]
}

function isReplacementAssignment(assignment) {
  return !!replacementAssignments.value[assignment]
}

function getReplacementTargets(assignment) {
  return replacementAssignments.value[assignment] || []
}

function toggleTargetAssignment(assignmentName) {
  const idx = newReplacementTargets.value.indexOf(assignmentName)
  if (idx >= 0) {
    newReplacementTargets.value.splice(idx, 1)
  } else {
    newReplacementTargets.value.push(assignmentName)
  }
}

// Extra credit assignment functions
function toggleExtraCredit(assignment) {
  if (extraCreditAssignments.value.has(assignment)) {
    extraCreditAssignments.value.delete(assignment)
  } else {
    extraCreditAssignments.value.add(assignment)
  }
  extraCreditAssignments.value = new Set(extraCreditAssignments.value) // Trigger reactivity
}

function isExtraCreditAssignment(assignment) {
  return extraCreditAssignments.value.has(assignment)
}

// Bulk assign helpers (non-drag option)
function toggleSelected(assignment) {
  const next = new Set(selectedAssignments.value)
  if (next.has(assignment)) {
    next.delete(assignment)
  } else {
    next.add(assignment)
  }
  selectedAssignments.value = next
}

function assignSelectedToCategory(categoryName) {
  if (!categoryName || selectedAssignments.value.size === 0) return
  const toAssign = Array.from(selectedAssignments.value)
  const updated = props.categories.map(cat => ({
    ...cat,
    assignments: cat.name === categoryName
      ? [...new Set([...cat.assignments, ...toAssign])]
      : cat.assignments.filter(a => !selectedAssignments.value.has(a))
  }))
  emit('update:categories', updated)
  selectedAssignments.value = new Set()
}

function clearSelection() {
  selectedAssignments.value = new Set()
}

function autoBalanceWeights() {
  const current = totalWeight.value || 100
  const updated = props.categories.map(c => c.extra_credit ? c : { ...c, weight: Math.round(((c.weight || 0) / current) * 100) })
  emit('update:categories', updated)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header with summary -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold">⚙️ Configure Categories & Weights</h2>
        <p class="text-base-content/60 mt-1">
          Step 1: create categories with weights. Step 2: assign assignments (drag or select) into each category.
        </p>
      </div>

      <!-- Status indicators -->
      <div class="flex items-center gap-3">
        <!-- Assignment progress -->
        <span class="badge badge-lg gap-1" :class="unassignedAssignments.length === 0 ? 'badge-success' : 'badge-warning'">
          {{ assignments.length - unassignedAssignments.length }}/{{ assignments.length }} assigned
        </span>
        <!-- Weight total indicator with progress bar -->
        <div class="flex items-center gap-2">
          <div :class="[
            'flex items-center gap-2 px-3 py-2 rounded-lg border-2 font-semibold',
            isWeightValid ? 'bg-success/10 border-success text-success' :
            isWeightOver ? 'bg-error/10 border-error text-error' :
            'bg-warning/10 border-warning text-warning'
          ]">
            <span class="text-lg font-bold">{{ totalWeight.toFixed(0) }}%</span>
            <span v-if="isWeightValid" class="text-lg">✓</span>
            <span v-else-if="!isWeightOver" class="text-sm">({{ remainingWeight.toFixed(0) }}% remaining)</span>
            <span v-else class="text-sm">({{ (totalWeight - 100).toFixed(0) }}% over!)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Validation banner -->
    <div v-if="!isWeightValid || unassignedAssignments.length > 0" class="alert bg-base-100 border border-warning/40 shadow-sm">
      <svg class="w-5 h-5 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div class="text-sm leading-snug">
        <div v-if="!isWeightValid" class="font-semibold text-warning">Weights must total 100% (excluding extra credit). Currently {{ totalWeight.toFixed(1) }}%.</div>
        <div v-if="unassignedAssignments.length > 0" class="text-base-content/80">{{ unassignedAssignments.length }} assignments still unassigned.</div>
      </div>
      <button v-if="!isWeightValid" @click="autoBalanceWeights" :disabled="totalWeight === 0" class="btn btn-ghost btn-xs text-primary">
        Auto-balance
      </button>
    </div>

    <!-- Compact Feature Toggles Row -->
    <div class="flex flex-wrap gap-3">
      <!-- Extra Credit Toggle -->
      <div :class="[
        'flex items-center gap-3 px-4 py-2 rounded-lg border-2 transition-all',
        extraCreditEnabled
          ? 'bg-warning/10 border-warning'
          : 'bg-base-200 border-base-300 hover:border-warning/50'
      ]">
        <label class="label cursor-pointer gap-2 p-0">
          <input
            type="checkbox"
            :checked="extraCreditEnabled"
            @change="$emit('update:extraCreditEnabled', $event.target.checked)"
            class="toggle toggle-sm toggle-warning" />
          <span class="font-semibold">⭐ Extra Credit</span>
        </label>
        <div class="tooltip tooltip-bottom" data-tip="Allow students to earn bonus points beyond 100%. Creates an 'Extra Credit' category with 0% weight.">
          <svg class="w-4 h-4 text-base-content/50 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div v-if="extraCreditEnabled" class="flex items-center gap-1 ml-2 pl-2 border-l border-warning/30">
          <span class="text-xs">Max:</span>
          <input
            type="number"
            :value="maxExtraCreditPercent"
            @input="$emit('update:maxExtraCreditPercent', parseFloat($event.target.value) || 5)"
            min="1"
            max="20"
            step="1"
            class="input input-bordered input-xs w-14 text-center font-bold" />
          <span class="text-xs">%</span>
          <span class="badge badge-warning badge-xs ml-1">{{ 100 + maxExtraCreditPercent }}%</span>
        </div>
      </div>

      <!-- Replacement Assignments Toggle -->
      <div :class="[
        'flex items-center gap-3 px-4 py-2 rounded-lg border-2 transition-all',
        props.replacementEnabled
          ? 'bg-info/10 border-info'
          : 'bg-base-200 border-base-300 hover:border-info/50'
      ]">
        <label class="label cursor-pointer gap-2 p-0">
          <input
            type="checkbox"
            :checked="props.replacementEnabled"
            @change="emit('update:replacementEnabled', $event.target.checked)"
            class="toggle toggle-sm toggle-info" />
          <span class="font-semibold">🔄 Replacement</span>
        </label>
        <div class="tooltip tooltip-bottom" data-tip="Use one assignment to replace the lowest score among selected assignments (only if higher).">
          <svg class="w-4 h-4 text-base-content/50 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div v-if="props.replacementEnabled && Object.keys(replacementAssignments).length > 0" class="badge badge-info badge-sm ml-1">
          {{ Object.keys(replacementAssignments).length }} rule{{ Object.keys(replacementAssignments).length > 1 ? 's' : '' }}
        </div>
      </div>
    </div>

    <!-- Replacement Rules Panel (only when enabled) -->
    <div v-if="props.replacementEnabled" class="bg-info/5 rounded-lg p-3 border border-info/30 space-y-3">
      <!-- Add Rule Section -->
      <div class="space-y-2">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-medium text-info">Replacer:</span>
          <select v-model="newReplacementAssignment" class="select select-bordered select-xs flex-1 max-w-xs">
            <option value="">Select assignment...</option>
            <option v-for="a in availableReplacerAssignments" :key="a" :value="a">{{ cleanAssignmentName(a) }}</option>
          </select>
        </div>

        <!-- Target Assignments Multi-Select -->
        <div v-if="newReplacementAssignment" class="pl-4 border-l-2 border-info/30">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-sm font-medium text-info">→ Can replace lowest of:</span>
            <span class="text-xs text-base-content/60">(select one or more)</span>
          </div>
          <div v-if="availableTargetAssignments.length === 0" class="text-sm text-base-content/60 italic">
            No assignments in categories yet. Assign some first.
          </div>
          <div v-else class="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
            <label v-for="target in availableTargetAssignments" :key="target.name"
                   class="cursor-pointer">
              <input type="checkbox"
                     :checked="newReplacementTargets.includes(target.name)"
                     @change="toggleTargetAssignment(target.name)"
                     class="hidden" />
              <span :class="[
                'badge badge-sm transition-all',
                newReplacementTargets.includes(target.name)
                  ? 'badge-info'
                  : 'badge-ghost hover:badge-info/50'
              ]">
                {{ cleanAssignmentName(target.name) }}
                <span class="text-xs opacity-60 ml-1">({{ target.category }})</span>
              </span>
            </label>
          </div>
          <div class="flex items-center gap-2 mt-2">
            <button
              @click="addReplacementRule"
              class="btn btn-info btn-xs"
              :disabled="newReplacementTargets.length === 0">
              + Add Rule
            </button>
            <span v-if="newReplacementTargets.length > 0" class="text-xs text-info">
              {{ newReplacementTargets.length }} selected
            </span>
          </div>
        </div>
      </div>

      <!-- Active Rules -->
      <div v-if="Object.keys(replacementAssignments).length > 0" class="pt-2 border-t border-info/30">
        <div class="text-xs font-medium text-info mb-2">Active Rules:</div>
        <div class="space-y-1">
          <div v-for="(targets, assignment) in replacementAssignments" :key="assignment"
               class="flex items-start gap-2 bg-info/10 rounded px-2 py-1">
            <span class="font-medium text-sm">{{ cleanAssignmentName(assignment) }}</span>
            <span class="text-info">→</span>
            <div class="flex-1 flex flex-wrap gap-1">
              <span v-for="t in targets" :key="t" class="badge badge-info badge-xs">
                {{ cleanAssignmentName(t) }}
              </span>
            </div>
            <button @click="clearReplacement(assignment)" class="btn btn-ghost btn-xs text-error hover:bg-error/20">×</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Two-Column Layout: Unassigned (Left) | Categories (Right) - Full Height -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
      <!-- LEFT COLUMN: Unassigned Assignments (40% on lg) - Full height with internal scroll -->
      <div class="lg:col-span-5 bg-base-200 rounded-box p-4 border-2 border-dashed border-base-300 flex flex-col min-h-0 lg:max-h-[calc(100vh-320px)]"
           @dragover.prevent="dragOverCategory = 'unassigned'"
           @dragleave="dragOverCategory = null"
           @drop.prevent="removeFromCategory(draggedAssignment); draggedAssignment = null; dragOverCategory = null">
        <div class="flex items-center justify-between mb-3 flex-shrink-0">
          <h3 class="text-base font-bold flex items-center gap-2">
            <div class="w-8 h-8 rounded-full bg-neutral text-neutral-content flex items-center justify-center font-bold text-sm">
              {{ unassignedAssignments.length }}
            </div>
            Unassigned
          </h3>
          <div v-if="unassignedAssignments.length > 0 && categories.length > 0" class="dropdown dropdown-end">
            <button tabindex="0" class="btn btn-primary btn-sm gap-1">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Assign All
            </button>
            <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-lg bg-base-100 rounded-box w-48">
              <li v-for="cat in categories" :key="cat.name">
                <a @click="assignAllTo(cat.name)" class="cursor-pointer">{{ cat.name }}</a>
              </li>
            </ul>
          </div>
        </div>

        <div v-if="unassignedAssignments.length === 0" class="alert alert-success py-2 text-sm flex-shrink-0">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="font-medium">All assigned!</span>
        </div>

        <!-- Grid layout for fixed-width cards -->
        <div v-else class="flex-1 overflow-y-auto space-y-2">
          <div class="flex items-center gap-2 bg-base-100 border border-base-300 rounded-lg p-2">
            <span class="text-xs text-base-content/70">Select then quick-assign:</span>
            <select class="select select-bordered select-xs w-40" @change="assignSelectedToCategory($event.target.value)">
              <option value="">Choose category…</option>
              <option v-for="cat in categories" :key="cat.name" :value="cat.name">{{ cat.name }}</option>
            </select>
            <span class="badge badge-ghost badge-sm">{{ selectedCount }} selected</span>
            <button class="btn btn-ghost btn-xs" @click="clearSelection" :disabled="selectedCount === 0">Clear</button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
            <div v-for="assignment in unassignedAssignments" :key="assignment"
                 draggable="true"
                 @dragstart="onDragStart(assignment, $event)"
                 @dragend="onDragEnd"
                 :class="[
                   'flex flex-col p-2 rounded-lg bg-base-100 border transition-all hover:shadow-md min-w-0',
                   isExtraCreditAssignment(assignment) ? 'border-warning bg-warning/10' : 'border-base-300',
                   isReplacementAssignment(assignment) ? 'ring-1 ring-info' : '',
                   selectedAssignments.has(assignment) ? 'border-primary ring-1 ring-primary/50' : ''
                 ]"
                 :title="assignment">
              <div class="flex items-start gap-2">
                <input type="checkbox" class="checkbox checkbox-xs mt-0.5"
                       :checked="selectedAssignments.has(assignment)"
                       @change="toggleSelected(assignment)" />
                <div class="flex flex-col gap-0.5 flex-1 min-w-0">
                  <div class="font-medium text-xs truncate" :title="assignment">
                    {{ cleanAssignmentName(assignment) }}
                  </div>
                  <div class="flex items-center gap-1 text-[10px] text-base-content/60 flex-wrap">
                    <span v-if="getPointsPossible(assignment)" class="badge badge-ghost badge-xs">{{ getPointsPossible(assignment) }} pts</span>
                    <span v-if="isExtraCreditAssignment(assignment)" class="badge badge-warning badge-xs">EC</span>
                    <span v-if="isReplacementAssignment(assignment)" class="badge badge-info badge-xs">
                      🔄 {{ getReplacementTargets(assignment).length }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT COLUMN: Categories (60% on lg) - Full height with internal scroll -->
      <div class="lg:col-span-7 flex flex-col min-h-0 lg:max-h-[calc(100vh-320px)] overflow-y-auto space-y-3 pr-1">
        <!-- Empty State - No Categories -->
        <div v-if="categories.length === 0" class="card bg-gradient-to-br from-primary/5 to-secondary/5 border-2 border-dashed border-primary/30">
          <div class="card-body items-center text-center py-8">
            <div class="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-3">
              <svg class="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 class="text-lg font-bold text-base-content">No Categories Yet</h3>
            <p class="text-base-content/60 text-sm max-w-sm mt-1">
              Create categories to organize your assignments (e.g., Homework, Exams, Projects).
              Then drag assignments into each category and set weights.
            </p>
            <button @click="showNewCategoryModal = true" class="btn btn-primary gap-2 mt-4">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Create Your First Category
            </button>
            <span class="text-xs text-base-content/50 mt-2">💡 Tip: Common categories include Homework, Quizzes, Exams, Projects</span>
          </div>
        </div>

        <!-- Category Cards -->
        <template v-else>
          <div v-for="(category, index) in categories" :key="category.name"
               @dragover="onDragOver(category.name, $event)"
               @dragleave="onDragLeave"
               @drop="onDrop(category.name, $event)"
               :class="[
                 'card border-2 transition-all',
                 dragOverCategory === category.name ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-base-300 bg-base-100',
                 category.extra_credit ? 'ring-2 ring-warning ring-offset-1' : ''
               ]">
            <div class="card-body p-3">
              <!-- Category Header Row -->
              <div class="flex items-center gap-3">
                <!-- Category name input with clear border styling -->
                <div class="form-control">
                  <input :value="category.name"
                         @input="updateCategory(index, 'name', $event.target.value)"
                         class="input input-sm font-bold flex-1 max-w-[200px] border-2 border-base-300 bg-base-100 focus:border-primary focus:outline-none transition-colors"
                         :disabled="category.extra_credit"
                         placeholder="Category name" />
                </div>
                <div class="flex items-center gap-2">
                  <!-- Extra Credit: Show "Bonus Only" badge instead of weight input -->
                  <div v-if="category.extra_credit" class="flex items-center gap-2">
                    <span class="badge badge-warning badge-sm font-semibold">⭐ Bonus Only</span>
                    <div class="tooltip tooltip-left" data-tip="Extra credit adds to your score but doesn't count toward the 100% total weight">
                      <svg class="w-4 h-4 text-warning cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <!-- Regular categories: Show weight input (emphasized) with clear styling -->
                  <div v-else class="form-control flex-row items-center gap-2 bg-primary/10 rounded-lg px-3 py-1.5 border border-primary/30">
                    <span class="text-sm font-semibold text-primary">Weight:</span>
                    <input :value="category.weight"
                           @input="updateCategory(index, 'weight', Number.parseFloat($event.target.value) || 0)"
                           type="number" min="0" max="100" step="5"
                           :aria-label="`Weight for ${category.name}`"
                           class="input input-sm w-16 text-center font-bold text-lg border-2 border-primary/50 bg-base-100 focus:border-primary focus:outline-none" />
                    <span class="text-sm font-semibold text-primary">%</span>
                  </div>
                </div>
                <button @click="removeCategory(index)" class="btn btn-ghost btn-xs text-error" title="Remove category">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <!-- Assignments Drop Zone -->
              <div class="mt-2 min-h-[50px] p-2 bg-base-200 rounded-lg">
                <div v-if="category.assignments.length === 0" class="text-center text-base-content/40 text-sm py-1">
                  ← Drag assignments here
                </div>
                <div v-else class="flex flex-wrap gap-1.5">
                  <span v-for="assignment in category.assignments" :key="assignment"
                        draggable="true"
                        @dragstart="onDragStart(assignment, $event)"
                        @dragend="onDragEnd"
                        class="badge badge-sm gap-1 cursor-grab active:cursor-grabbing group hover:badge-error transition-all"
                        :class="category.extra_credit ? 'badge-warning' : 'badge-primary'"
                        :title="assignment">
                    {{ shortenName(assignment, 18) }}
                    <button @click="removeFromCategory(assignment)" class="opacity-0 group-hover:opacity-100">×</button>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Add Category Button -->
          <button @click="showNewCategoryModal = true"
                  class="btn btn-outline btn-block gap-2 border-dashed">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Category
          </button>
        </template>
      </div>
    </div>

    <!-- New Category Modal - Fixed styling with proper borders and backdrop -->
    <Teleport to="body">
      <div v-if="showNewCategoryModal" class="fixed inset-0 z-[9999] flex items-center justify-center">
        <!-- Full-screen backdrop overlay -->
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showNewCategoryModal = false"></div>

        <!-- Modal content -->
        <div class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border-2 border-base-300 w-full max-w-md mx-4 overflow-hidden">
          <!-- Modal header -->
          <div class="bg-primary/10 border-b border-base-300 px-6 py-4">
            <h3 class="font-bold text-xl text-base-content flex items-center gap-2">
              <span class="text-2xl">📁</span>
              Create New Category
            </h3>
          </div>

          <!-- Modal body -->
          <div class="px-6 py-5 space-y-5">
            <!-- Category Name Field -->
            <div class="form-control">
              <label class="label pb-1">
                <span class="label-text font-semibold text-base">Category Name</span>
              </label>
              <input
                v-model="newCategoryName"
                type="text"
                placeholder="e.g., Homework, Exams, Projects"
                class="input input-bordered border-2 border-base-300 focus:border-primary focus:outline-none bg-base-100 w-full text-base"
                @keyup.enter="addCategory" />
            </div>

            <!-- Weight Field -->
            <div class="form-control">
              <label class="label pb-1">
                <span class="label-text font-semibold text-base">Weight (%)</span>
              </label>
              <div class="flex items-center gap-3">
                <input
                  v-model.number="newCategoryWeight"
                  type="number"
                  min="0"
                  max="100"
                  step="5"
                  class="input input-bordered border-2 border-base-300 focus:border-primary focus:outline-none bg-base-100 w-28 text-center text-lg font-bold" />
                <span class="text-base-content/60 text-sm">of total grade</span>
              </div>
            </div>
          </div>

          <!-- Modal footer -->
          <div class="bg-base-200/50 border-t border-base-300 px-6 py-4 flex justify-end gap-3">
            <button
              @click="showNewCategoryModal = false"
              class="btn btn-ghost border-2 border-base-300 hover:bg-base-300">
              Cancel
            </button>
            <button
              @click="addCategory"
              class="btn btn-primary shadow-lg hover:shadow-xl transition-shadow"
              :disabled="!newCategoryName.trim()">
              <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Create Category
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Replacement Assignment Modal - Fixed styling with proper borders and backdrop -->
    <Teleport to="body">
      <div v-if="showReplacementModal" class="fixed inset-0 z-[9999] flex items-center justify-center">
        <!-- Full-screen backdrop overlay -->
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showReplacementModal = false"></div>

        <!-- Modal content -->
        <div class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border-2 border-base-300 w-full max-w-md mx-4 overflow-hidden">
          <!-- Modal header -->
          <div class="bg-info/10 border-b border-base-300 px-6 py-4">
            <h3 class="font-bold text-xl text-base-content flex items-center gap-2">
              <span class="text-2xl">🔄</span>
              Set Replacement Assignment
            </h3>
          </div>

          <!-- Modal body -->
          <div class="px-6 py-5 space-y-4">
            <p class="text-base-content/70">
              This assignment will replace the lowest score in the selected category.
            </p>

            <div class="bg-info/10 border border-info/30 rounded-lg px-4 py-3">
              <span class="font-medium text-info">{{ selectedReplacementAssignment }}</span>
            </div>

            <div class="form-control">
              <label class="label pb-1">
                <span class="label-text font-semibold text-base">Replace lowest score in:</span>
              </label>
              <select
                v-model="replacementTargetCategory"
                class="select select-bordered border-2 border-base-300 focus:border-info focus:outline-none bg-base-100 w-full">
                <option value="">Select a category...</option>
                <option v-for="cat in categories" :key="cat.name" :value="cat.name">{{ cat.name }}</option>
              </select>
            </div>

            <p class="text-sm text-base-content/60 bg-base-200 rounded-lg p-3">
              💡 Example: If a student scores 80% on this assignment and their lowest homework is 60%,
              the 60% will be replaced with 80%.
            </p>
          </div>

          <!-- Modal footer -->
          <div class="bg-base-200/50 border-t border-base-300 px-6 py-4 flex justify-end gap-3">
            <button
              @click="showReplacementModal = false"
              class="btn btn-ghost border-2 border-base-300 hover:bg-base-300">
              Cancel
            </button>
            <button
              @click="setReplacementAssignment"
              class="btn btn-info shadow-lg hover:shadow-xl transition-shadow"
              :disabled="!replacementTargetCategory">
              Set Replacement
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
