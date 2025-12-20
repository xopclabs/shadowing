<script setup lang="ts">
import { RouterView } from "vue-router";
</script>

<template>
  <div class="min-h-screen flex flex-col safe-top safe-bottom">
    <!-- Header -->
    <header
      class="px-4 py-3 border-b border-noche-800 bg-noche-900/80 backdrop-blur-sm sticky top-0 z-50"
    >
      <div class="max-w-2xl mx-auto flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-2">
          <img src="/vite.svg" alt="Logo" class="w-8 h-8" />
          <span class="font-display font-bold text-xl text-sol-400"
            >Shadowing</span
          >
        </router-link>
        <nav class="flex items-center gap-4">
          <router-link
            to="/"
            class="text-noche-400 hover:text-noche-100 transition-colors"
            active-class="text-sol-400"
          >
            Practice
          </router-link>
          <router-link
            to="/history"
            class="text-noche-400 hover:text-noche-100 transition-colors"
            active-class="text-sol-400"
          >
            History
          </router-link>
        </nav>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
