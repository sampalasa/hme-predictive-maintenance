(function () {
    const root = document.documentElement;
    const STORAGE_KEY = "hme-theme";

    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }

    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        applyTheme(saved);
    }

    const toggleBtn = document.getElementById("themeToggle");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", function () {
            const current = root.getAttribute("data-theme") || "light";
            applyTheme(current === "dark" ? "light" : "dark");
        });
    }

    const burger = document.getElementById("sidebarBurger");
    const sidebar = document.getElementById("sidebar");
    if (burger && sidebar) {
        burger.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
    }
})();
