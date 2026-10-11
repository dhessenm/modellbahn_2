import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
    },
    {
      path: '/throttle',
      name: 'throttle',
      component: () => import('../views/CabView.vue'),
    },
    {
      path: '/turnouts',
      name: 'turnouts',
      component: () => import('../views/TurnoutView.vue'),
    },
    {
      path: '/detectors',
      name: 'detectors',
      component: () => import('../views/DetectorView.vue'),
    },
    {
      path: '/track-plan',
      name: 'track-plan',
      component: () => import('../views/TrackPlanView.vue'),
    },
    {
      path: '/track-edit',
      name: 'track-edit',
      component: () => import('../views/TrackPlanEditView.vue'),
    },
  ],
})

export default router
