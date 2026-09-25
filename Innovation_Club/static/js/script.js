// Counts up the hero stats once, on page load, if the user hasn't
// asked for reduced motion. This is the site's one deliberate motion
// moment — everything else stays still.

document.addEventListener("DOMContentLoaded", () => {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  const statRow = document.querySelector("[data-animate-stats]");
  if (!statRow) return;

  const nums = statRow.querySelectorAll(".stat-num");

  nums.forEach((el) => {
    const target = parseInt(el.dataset.count, 10) || 0;

    if (prefersReducedMotion || target === 0) {
      el.textContent = target;
      return;
    }

    const duration = 700;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      el.textContent = Math.round(eased * target);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
});
