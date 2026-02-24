<template>
  <div class="min-h-screen bg-gray-900 flex">
    <!-- Sidebar -->
    <aside class="w-56 bg-gray-800 border-r border-gray-700 flex flex-col">
      <div class="px-4 py-4 border-b border-gray-700">
        <router-link to="/" class="text-sm text-gray-400 hover:text-white">← Back to Maps</router-link>
        <h2 class="text-lg font-semibold mt-2">Admin</h2>
      </div>
      <nav class="p-4 space-y-1">
        <router-link
          to="/admin/users"
          class="block px-3 py-2 rounded-md text-sm hover:bg-gray-700"
          active-class="bg-gray-700 text-white"
        >Users</router-link>
        <router-link
          to="/admin/roles"
          class="block px-3 py-2 rounded-md text-sm hover:bg-gray-700"
          active-class="bg-gray-700 text-white"
        >Roles & Permissions</router-link>
        <router-link
          to="/admin/maps"
          class="block px-3 py-2 rounded-md text-sm hover:bg-gray-700"
          active-class="bg-gray-700 text-white"
        >Maps</router-link>
      </nav>
    </aside>
    <!-- Content -->
    <main class="flex-1 p-8 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
