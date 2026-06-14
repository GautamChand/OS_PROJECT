// animations.js — Premium micro-animations for dashboard

document.addEventListener('DOMContentLoaded', () => {
    initScrollAnimations();
});

// Initialize fade-in and slide-up animations using IntersectionObserver
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.glass-card, .stat-card, .chart-container, .dashboard-grid, .file-table-container');
    
    const observerOptions = {
        threshold: 0.05,
        rootMargin: '0px 0px -20px 0px'
    };
    
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(el => {
        // Add initial setup style
        el.style.opacity = '0';
        el.style.transform = 'translateY(15px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        
        observer.observe(el);
    });
    
    // Inject animation class stylesheet rules dynamically
    const style = document.createElement('style');
    style.innerHTML = `
        .animate-in {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
}

// Animate counting numbers
function animateCounter(elementId, targetValue, duration = 1500, formatFn = null) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    let startTimestamp = null;
    const startValue = 0;
    
    function step(timestamp) {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentValue = progress * (targetValue - startValue) + startValue;
        
        if (formatFn) {
            element.innerHTML = formatFn(currentValue);
        } else {
            element.innerHTML = Math.floor(currentValue).toLocaleString();
        }
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            if (formatFn) {
                element.innerHTML = formatFn(targetValue);
            } else {
                element.innerHTML = targetValue.toLocaleString();
            }
        }
    }
    
    window.requestAnimationFrame(step);
}
