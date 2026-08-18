import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import './styles/base.css'
import './styles/app.css'
import './styles/trends.css'
import './styles/optimization.css'
import './styles/pdd-auth.css'

createApp(App).use(createPinia()).use(router).mount('#app')
