import { createRouter, createWebHistory } from 'vue-router'
import CabView from '../views/CabView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'cab',
      component: CabView,
    },
  ],
})

export default router
