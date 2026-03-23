import type { Directive } from 'vue';

export const revealDirective: Directive = {
  mounted(el, binding) {
    // 采用顶级官网常用的 ease-out-expo 电影级顺滑贝塞尔曲线，以及更长的过渡时间
    el.classList.add('opacity-0', 'transition-all', 'duration-[1500ms]', 'ease-[cubic-bezier(0.16,1,0.3,1)]');
    
    if (binding.arg === 'slide-left') {
      el.classList.add('translate-x-48');
    } else if (binding.arg === 'slide-right') {
      el.classList.add('-translate-x-48');
    } else if (binding.arg === 'scale-up') {
      el.classList.add('scale-[0.85]');
    } else if (binding.arg === 'zoom-out') {
      el.classList.add('scale-[1.10]', 'blur-xl');
    } else if (binding.arg === 'blur-in') {
      el.classList.add('blur-2xl', 'translate-y-24', 'scale-95');
    } else if (binding.arg === 'fade') {
      // 纯淡入
    } else {
      el.classList.add('translate-y-32');
    }

    const delay = binding.value?.delay || 0;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setTimeout(() => {
              el.classList.remove('opacity-0', 'translate-y-32', 'translate-x-48', '-translate-x-48', 'scale-[0.85]', 'scale-[1.10]', 'blur-xl', 'blur-2xl', 'translate-y-24', 'scale-95');
              el.classList.add('opacity-100', 'translate-y-0', 'translate-x-0', 'scale-100', 'blur-none');
            }, delay);
            observer.unobserve(el);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );
    
    setTimeout(() => {
        observer.observe(el);
    }, 50);
  }
};
