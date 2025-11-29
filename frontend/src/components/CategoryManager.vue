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
  // Remove all parenthesized text (including the parentheses)
  cleaned = cleaned.replace(/\s*\(.*?\)/g, '')
  // Remove "- Requires Respondus LockDown Browser" and similar
  cleaned = cleaned.replace(/[-–]\s*Requires\s+Respondus.*$/i, '')
  // Remove extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  return cleaned
}

// Helper: Generate a consistent color for a category name
function getCategoryColor(name) {
  if (name === 'Extra Credit') return 'warning'
  
  const colors = ['primary', 'secondary', 'accent', 'info', 'success', 'error']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
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
  <div class="h-full flex flex-col gap-4">
    <!-- Toolbar: Stats & Settings -->
    <div class="bg-base-100 p-3 rounded-xl border border-base-200 shadow-sm shrink-0 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-3" :class="isWeightValid ? 'text-success' : 'text-warning'">
            <div class="radial-progress text-xs font-bold bg-base-200 border-4 border-base-200" :style="`--value:${Math.min(totalWeight, 100)}; --size:3rem; --thickness: 4px;`">{{ totalWeight.toFixed(0) }}%</div>
            <div class="flex flex-col leading-tight">
              <span class="text-xs font-bold uppercase tracking-wider opacity-70">Total Weight</span>
              <span class="text-sm font-bold" v-if="isWeightValid">Perfectly Balanced</span>
              <span class="text-sm font-bold" v-else-if="totalWeight > 100">{{ (totalWeight - 100).toFixed(0) }}% Over</span>
              <span class="text-sm font-bold" v-else>{{ (100 - totalWeight).toFixed(0) }}% Remaining</span>
            </div>
          </div>
          <div class="flex flex-col leading-tight">
            <span class="text-xs font-bold uppercase tracking-wider opacity-70">Assignments</span>
            <span class="text-sm font-bold">{{ assignments.length - unassignedAssignments.length }} / {{ assignments.length }} mapped</span>
          </div>
          <button class="btn btn-primary btn-sm shadow-sm" @click="showNewCategoryModal = true">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
            New Category
          </button>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <label class="flex items-center gap-2 text-sm font-medium">
            <span class="text-base-content/70">Extra Credit</span>
            <input type="checkbox" :checked="extraCreditEnabled" @change="$emit('update:extraCreditEnabled', $event.target.checked)" class="toggle toggle-warning toggle-sm" aria-label="Toggle extra credit" />
            <div v-if="extraCreditEnabled" class="flex items-center gap-1 text-xs bg-base-200 rounded-lg px-2 py-1 border border-base-300">
              <span class="opacity-70">Max</span>
              <input type="number" :value="maxExtraCreditPercent" @input="$emit('update:maxExtraCreditPercent', parseFloat($event.target.value) || 5)" class="input input-ghost input-xs w-14 text-center font-bold" />
              <span class="opacity-70">%</span>
            </div>
          </label>
          <label class="flex items-center gap-2 text-sm font-medium">
            <span class="text-base-content/70">Grade Replacement</span>
            <input type="checkbox" :checked="replacementEnabled" @change="emit('update:replacementEnabled', $event.target.checked)" class="toggle toggle-info toggle-sm" aria-label="Toggle grade replacement" />
          </label>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-3 text-xs text-base-content/70">
        <span class="badge badge-ghost">Weights must total 100% (bonus excluded)</span>
        <span class="badge badge-ghost">Optional Homework replaces lowest of HW1 or HW2 when enabled</span>
        <span class="badge badge-ghost">Drag or multi-select to map faster</span>
      </div>
    </div>

    <!-- Validation Banner (only if error) -->
    <div v-if="!isWeightValid" class="alert alert-warning shadow-sm py-2 rounded-lg shrink-0">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      <div class="flex-1 text-sm">
        <span class="font-bold">Adjust weights:</span> Totals are {{ totalWeight.toFixed(1) }}%. Aim for exactly 100% (bonus excluded).
      </div>
      <button @click="autoBalanceWeights" :disabled="totalWeight === 0" class="btn btn-sm btn-outline">
        Auto-balance
      </button>
    </div>

    <!-- Main Drag & Drop Area -->
    <div class="flex-1 min-h-0 grid lg:grid-cols-[0.4fr_1fr] gap-4 lg:gap-6 overflow-hidden">
       <!-- Left: Unassigned (Source) -->
       <div class="flex flex-col bg-base-100 rounded-xl border border-base-200 shadow-sm overflow-hidden"
            @dragover.prevent="dragOverCategory = 'unassigned'"
            @dragleave="dragOverCategory = null"
            @drop.prevent="removeFromCategory(draggedAssignment); draggedAssignment = null; dragOverCategory = null">
          
          <div class="p-3 border-b border-base-200 bg-base-50/50 flex justify-between items-center shrink-0">
             <div class="flex items-center gap-2">
               <div class="w-2 h-2 rounded-full" :class="unassignedAssignments.length > 0 ? 'bg-warning' : 'bg-success'"></div>
               <h3 class="font-bold text-sm text-base-content/80">Unassigned Items</h3>
             </div>
             
             <div class="flex items-center gap-2">
                <span class="badge badge-sm font-mono">{{ unassignedAssignments.length }}</span>
                <div v-if="unassignedAssignments.length > 0 && categories.length > 0" class="dropdown dropdown-end">
                  <button tabindex="0" class="btn btn-xs btn-secondary btn-outline" title="Assign All">
                    Assign all
                  </button>
                  <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-48 border border-base-200">
                    <li class="menu-title px-2 py-1 text-xs opacity-50">Assign all to:</li>
                    <li v-for="cat in categories" :key="cat.name">
                      <a @click="assignAllTo(cat.name)">{{ cat.name }}</a>
                    </li>
                  </ul>
                </div>
             </div>
          </div>

          <div class="flex-1 overflow-y-auto p-3 bg-base-200/30">
             <div v-if="unassignedAssignments.length === 0" class="h-full flex flex-col items-center justify-center text-base-content/40 p-4 text-center">
                <svg class="w-12 h-12 mb-2 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <p class="text-sm font-medium">All assignments mapped!</p>
             </div>
             <div v-else class="flex flex-wrap gap-2 content-start">
                 <div v-for="assignment in unassignedAssignments" :key="assignment"
                      draggable="true"
                      @dragstart="onDragStart(assignment, $event)"
                      @dragend="onDragEnd"
                      :class="[
                        'group flex items-center gap-2 px-3 py-2 rounded-lg bg-base-100 border shadow-sm cursor-grab active:cursor-grabbing hover:border-primary/50 hover:shadow-md transition-all max-w-[210px]',
                        selectedAssignments.has(assignment) ? 'border-primary ring-1 ring-primary/50' : 'border-base-200'
                      ]">
                    <div class="w-1.5 h-1.5 rounded-full bg-base-300 group-hover:bg-primary/50 transition-colors shrink-0"></div>
                    <div class="flex-1 min-w-0">
                       <div class="font-medium text-xs truncate leading-tight" :title="assignment">{{ cleanAssignmentName(assignment) }}</div>
                    </div>
                    <input type="checkbox" class="checkbox checkbox-xs opacity-0 group-hover:opacity-100 checked:opacity-100 transition-opacity shrink-0" 
                           :checked="selectedAssignments.has(assignment)"
                           @change="toggleSelected(assignment)" aria-label="Select assignment" />
                 </div>
              </div>
          </div>
       </div>

       <!-- Right: Categories (Target) -->
       <div class="flex flex-col overflow-hidden">
          <div v-if="categories.length === 0" class="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-base-300 rounded-xl bg-base-50/50 p-8 text-center">
             <div class="w-16 h-16 rounded-full bg-base-200 flex items-center justify-center mb-4">
               <svg class="w-8 h-8 text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
             </div>
             <h3 class="font-bold text-lg">No Categories Yet</h3>
             <p class="text-base-content/60 max-w-sm mt-1 mb-4">Create categories like "Homework" or "Exams" to start organizing your gradebook.</p>
             <button @click="showNewCategoryModal = true" class="btn btn-primary">Create Category</button>
          </div>

          <div v-else class="flex-1 min-h-0 overflow-y-auto">
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 pb-4">
               <div v-for="(category, index) in categories" :key="category.name"
                    @dragover="onDragOver(category.name, $event)"
                    @dragleave="onDragLeave"
                    @drop="onDrop(category.name, $event)"
                    :class="[
                      'card bg-base-100 border transition-all duration-200 h-full',
                      dragOverCategory === category.name ? 'border-primary ring-2 ring-primary/20 scale-[1.01] shadow-lg' : 'border-base-300 shadow-sm hover:border-base-content/20',
                      category.extra_credit ? 'bg-warning/5 border-warning/30' : ''
                    ]">
                  <div class="card-body p-4 flex flex-col gap-3">
                     <!-- Category Header -->
                     <div class="flex items-start justify-between gap-2">
                        <div class="flex-1 min-w-0">
                           <div class="flex items-center gap-2">
                              <h3 class="font-bold text-lg truncate" :title="category.name">{{ cleanAssignmentName(category.name) }}</h3>
                              <span v-if="category.extra_credit" class="badge badge-warning badge-xs">Bonus</span>
                           </div>
                           <div class="text-xs text-base-content/60 mt-0.5">
                              {{ category.assignments.length }} items
                           </div>
                        </div>
                        
                        <div class="flex items-center gap-2">
                           <div v-if="!category.extra_credit" class="flex items-center bg-base-200 rounded-lg px-2 py-1 border border-base-300">
                              <input :value="category.weight"
                                     @input="updateCategory(index, 'weight', Number.parseFloat($event.target.value) || 0)"
                                     type="number" min="0" max="100" step="5"
                                     class="input input-xs w-12 text-right font-bold bg-transparent border-none focus:outline-none p-0" />
                              <span class="text-xs font-bold text-base-content/50 ml-1">%</span>
                           </div>
                           <button @click="removeCategory(index)" class="btn btn-ghost btn-xs btn-square text-error/70 hover:text-error hover:bg-error/10">
                              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                           </button>
                        </div>
                     </div>

                     <!-- Assignments List -->
                     <div class="min-h-[90px] bg-base-200/50 rounded-lg p-2 transition-colors"
                          :class="dragOverCategory === category.name ? 'bg-primary/5' : ''">
                        <div v-if="category.assignments.length === 0" class="h-full flex items-center justify-center text-xs text-base-content/40 italic py-4">
                           Drag assignments here
                        </div>
                         <div v-else class="flex flex-wrap gap-2">
                            <div v-for="assignment in category.assignments" :key="assignment"
                                 draggable="true"
                                 @dragstart="onDragStart(assignment, $event)"
                                 @dragend="onDragEnd"
                                 class="group flex items-center gap-2 px-3 py-2 rounded-lg bg-base-100 border border-base-200 shadow-sm cursor-grab active:cursor-grabbing hover:shadow-md transition-all max-w-[200px]">
                               <div class="w-1.5 h-1.5 rounded-full transition-colors shrink-0" :class="`bg-${getCategoryColor(category.name)}`"></div>
                               <div class="flex-1 min-w-0">
                                  <div class="font-medium text-xs truncate leading-tight" :title="assignment">{{ cleanAssignmentName(assignment) }}</div>
                               </div>
                               <button @click="removeFromCategory(assignment)" class="btn btn-ghost btn-xs btn-circle w-4 h-4 min-h-0 opacity-0 group-hover:opacity-100 text-error/70 hover:text-error hover:bg-error/10 transition-opacity shrink-0" aria-label="Remove assignment">
                                  <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                               </button>
                            </div>
                         </div>
                     </div>
                  </div>
               </div>
               
               <!-- Add Category Card (at end of grid) -->
               <button @click="showNewCategoryModal = true" class="card border-2 border-dashed border-base-300 bg-base-50/50 hover:border-primary/50 hover:bg-primary/5 transition-all h-full min-h-[150px] flex items-center justify-center group">
                  <div class="flex flex-col items-center gap-2 text-base-content/50 group-hover:text-primary transition-colors">
                     <div class="w-10 h-10 rounded-full bg-base-200 group-hover:bg-primary/20 flex items-center justify-center transition-colors">
                        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
                     </div>
                     <span class="font-bold text-sm">Add Another Category</span>
                  </div>
               </button>
            </div>
          </div>
       </div>
    </div>

    <!-- Replacement Rules Panel (only when enabled) -->
    <div v-if="replacementEnabled" class="bg-info/5 rounded-xl p-4 border border-info/20 space-y-3 shrink-0">
      <div class="flex items-center gap-2 text-info font-bold text-sm">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
        Grade Replacement Rules
      </div>
      
      <!-- Add Rule Section -->
      <div class="flex flex-wrap items-end gap-3 bg-base-100 p-3 rounded-lg border border-base-200">
        <div class="form-control w-full sm:w-auto sm:flex-1 min-w-[200px]">
          <label class="label py-1 text-xs font-medium text-base-content/70">Replacer Assignment (Highest Score)</label>
          <select v-model="newReplacementAssignment" class="select select-sm select-bordered w-full">
            <option value="">Select assignment...</option>
            <option v-for="a in availableReplacerAssignments" :key="a" :value="a">{{ cleanAssignmentName(a) }}</option>
          </select>
        </div>

        <div class="form-control w-full sm:w-auto sm:flex-[2] min-w-[200px]">
           <label class="label py-1 text-xs font-medium text-base-content/70">Target Assignments (Lowest Score Replaced)</label>
           <div class="dropdown w-full">
             <div tabindex="0" role="button" class="select select-sm select-bordered w-full flex items-center justify-between">
               <span v-if="newReplacementTargets.length === 0" class="opacity-50">Select targets...</span>
               <span v-else class="truncate">{{ newReplacementTargets.length }} selected</span>
             </div>
             <div tabindex="0" class="dropdown-content z-[1] card card-compact w-full p-2 shadow bg-base-100 border border-base-200 mt-1 max-h-60 overflow-y-auto">
                <div v-if="availableTargetAssignments.length === 0" class="p-2 text-xs opacity-50">No available targets</div>
                <label v-for="target in availableTargetAssignments" :key="target.name" class="label cursor-pointer justify-start gap-2 hover:bg-base-200 rounded p-1">
                  <input type="checkbox" :checked="newReplacementTargets.includes(target.name)" @change="toggleTargetAssignment(target.name)" class="checkbox checkbox-xs checkbox-info" />
                  <span class="text-xs truncate" :title="target.name">{{ cleanAssignmentName(target.name) }} <span class="opacity-50">({{ target.category }})</span></span>
                </label>
             </div>
           </div>
        </div>

        <button @click="addReplacementRule" class="btn btn-sm btn-info text-white" :disabled="!newReplacementAssignment || newReplacementTargets.length === 0">
          Add Rule
        </button>
      </div>

      <!-- Active Rules -->
      <div v-if="Object.keys(replacementAssignments).length > 0" class="flex flex-wrap gap-2">
         <div v-for="(targets, assignment) in replacementAssignments" :key="assignment" class="badge badge-info gap-2 py-3 h-auto pl-3 pr-1">
            <div class="flex flex-col text-xs text-left">
               <span class="font-bold">{{ cleanAssignmentName(assignment) }}</span>
               <span class="opacity-80">replaces {{ targets.length }} items</span>
            </div>
            <button @click="clearReplacement(assignment)" class="btn btn-ghost btn-xs btn-circle h-5 w-5 min-h-0 text-white/70 hover:text-white hover:bg-white/20">×</button>
         </div>
      </div>
    </div>

    <!-- Modals (Teleported) -->
    <Teleport to="body">
      <!-- New Category Modal -->
      <div v-if="showNewCategoryModal" class="fixed inset-0 z-[9999] flex items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showNewCategoryModal = false"></div>
        <div class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border border-base-200 w-full max-w-md overflow-hidden transform transition-all">
          <div class="px-6 py-4 border-b border-base-200 bg-base-50/50 flex justify-between items-center">
            <h3 class="font-bold text-lg">New Category</h3>
            <button @click="showNewCategoryModal = false" class="btn btn-ghost btn-sm btn-circle">✕</button>
          </div>
          <div class="p-6 space-y-4">
            <div class="form-control">
              <label class="label font-medium">Name</label>
              <input v-model="newCategoryName" type="text" placeholder="e.g. Homework" class="input input-bordered w-full" @keyup.enter="addCategory" />
            </div>
            <div class="form-control">
              <label class="label font-medium">Weight (%)</label>
              <input v-model.number="newCategoryWeight" type="number" class="input input-bordered w-full" @keyup.enter="addCategory" />
            </div>
          </div>
          <div class="px-6 py-4 bg-base-50/50 border-t border-base-200 flex justify-end gap-2">
            <button @click="showNewCategoryModal = false" class="btn btn-ghost">Cancel</button>
            <button @click="addCategory" class="btn btn-primary" :disabled="!newCategoryName">Create</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
