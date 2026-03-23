import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './index.css'
import { revealDirective } from './directives/reveal'

const app = createApp(App)

app.use(router)
app.directive('reveal', revealDirective)
app.mount('#app')
