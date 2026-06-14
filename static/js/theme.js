// theme.js — Dark/Light theme manager

(function() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    updateThemeUI(savedTheme);
});

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeUI(newTheme);
    
    // Dispatch custom event for charts to update colors
    const event = new CustomEvent('themeChanged', { detail: { theme: newTheme } });
    document.dispatchEvent(event);
}

function updateThemeUI(theme) {
    // If we have a theme toggle button in the DOM (base.html does), update any theme specific icons/attributes
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
        toggleBtn.setAttribute('title', `Switch to ${theme === 'light' ? 'dark' : 'light'} mode`);
    }
}
