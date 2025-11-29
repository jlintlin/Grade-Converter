<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['upload-success', 'upload-error'])
const props = defineProps({
  isLoading: Boolean
})

const isDragging = ref(false)
const isUploading = ref(false)
const selectedFile = ref(null)

// API base URL
const API_URL = import.meta.env.VITE_API_URL || ''

function handleDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragging.value = false
  
  const files = e.dataTransfer.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

function handleFile(file) {
  if (!file.name.endsWith('.csv')) {
    emit('upload-error', 'Please select a CSV file')
    return
  }
  selectedFile.value = file
}

async function uploadFile() {
  if (!selectedFile.value) return
  
  isUploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const response = await axios.post(`${API_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    emit('upload-success', response.data)
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to upload file'
    emit('upload-error', message)
  } finally {
    isUploading.value = false
  }
}

function clearFile() {
  selectedFile.value = null
}
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Drop Zone - Takes full remaining height -->
    <div
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      :class="[
        'flex-1 border-4 border-dashed rounded-none sm:rounded-b-xl p-8 text-center transition-all cursor-pointer flex flex-col items-center justify-center relative overflow-hidden group',
        isDragging
          ? 'border-primary bg-primary/5'
          : 'border-base-200 hover:border-primary/30 hover:bg-base-50'
      ]"
    >
      <!-- Background Pattern -->
      <div class="absolute inset-0 opacity-[0.03] pointer-events-none" 
           style="background-image: radial-gradient(#6366f1 1px, transparent 1px); background-size: 24px 24px;">
      </div>

      <div v-if="!selectedFile" class="flex flex-col items-center justify-center max-w-lg mx-auto z-10">
        <!-- Upload Icon -->
        <div class="w-32 h-32 rounded-full bg-base-100 shadow-lg flex items-center justify-center mb-8 group-hover:scale-110 group-hover:shadow-xl transition-all duration-300 border border-base-200">
          <svg class="w-14 h-14 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        
        <h3 class="text-2xl font-bold text-base-content mb-3">Drag & Drop CSV File</h3>
        <p class="text-base text-base-content/60 mb-10 max-w-xs mx-auto leading-relaxed">
          Drag your Canvas gradebook export here or click the button below.
        </p>
        
        <label class="btn btn-primary btn-lg px-10 h-14 text-lg shadow-xl shadow-primary/20 hover:shadow-2xl hover:-translate-y-1 transition-all border-none bg-gradient-to-r from-primary to-secondary text-white">
          <svg class="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Browse Files
          <input type="file" accept=".csv" class="hidden" @change="handleFileSelect" />
        </label>
        
        <div class="mt-12 flex items-center gap-2 text-sm text-base-content/40 font-medium">
           <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
           Supports standard Canvas CSV exports
        </div>
      </div>

      <!-- Selected File State -->
      <div v-else class="flex flex-col items-center justify-center text-center w-full max-w-xl z-10">
        <div class="w-24 h-24 rounded-full bg-success/10 flex items-center justify-center mb-8 animate-bounce-small">
          <svg class="w-12 h-12 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        
        <div class="bg-base-100 border border-base-200 rounded-2xl p-6 w-full mb-10 shadow-lg">
           <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-xl bg-base-200 flex items-center justify-center shrink-0">
                 <svg class="w-7 h-7 text-base-content/50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <div class="text-left flex-1 min-w-0">
                 <p class="font-bold text-lg truncate" :title="selectedFile.name">{{ selectedFile.name }}</p>
                 <p class="text-sm text-base-content/60">{{ (selectedFile.size / 1024).toFixed(1) }} KB</p>
              </div>
              <button @click="clearFile" class="btn btn-ghost btn-sm btn-square text-error/70 hover:text-error hover:bg-error/10" title="Remove file">
                 <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
           </div>
        </div>

        <div class="flex flex-col sm:flex-row justify-center gap-4 w-full">
          <button
            @click="clearFile"
            class="btn btn-outline border-base-300 hover:bg-base-200 hover:border-base-300 text-base-content/70 h-12 px-8"
          >
            Cancel
          </button>
          <button
            @click="uploadFile"
            :disabled="isUploading"
            class="btn btn-primary h-12 px-10 gap-3 shadow-xl shadow-primary/20 hover:shadow-2xl hover:-translate-y-1 transition-all flex-1 sm:flex-none sm:min-w-[200px] text-lg font-bold"
          >
            <span v-if="isUploading" class="loading loading-spinner loading-sm"></span>
            <template v-else>
               Process Grades
               <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
               </svg>
            </template>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

