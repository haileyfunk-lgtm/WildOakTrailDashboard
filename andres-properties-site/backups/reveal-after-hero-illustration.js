(function () {
  var SELECTOR = '.reveal-up, .reveal-scale';

  if (!('IntersectionObserver' in window)) {
    document.querySelectorAll(SELECTOR).forEach(function (el) {
      el.classList.add('is-visible');
    });
    return;
  }
  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll(SELECTOR).forEach(function (el) {
      io.observe(el);
    });
  });
})();

(function () {
  // Subtle mouse-parallax on the hero background illustration, same
  // technique as rankandfound.com's hero chart: track cursor position
  // relative to the hero section and translate by a small fraction of
  // the offset. Skipped on narrow viewports (illustration is hidden there
  // anyway) and under reduced-motion.
  var hero = document.querySelector('#home');
  var illustration = document.querySelector('.hero-bg-illustration');
  if (!hero || !illustration) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.innerWidth <= 921) return;

  hero.addEventListener('mousemove', function (e) {
    var r = hero.getBoundingClientRect();
    var x = e.clientX - r.left - r.width / 2;
    var y = e.clientY - r.top - r.height / 2;
    illustration.style.transform = 'translate(' + (x * 0.012).toFixed(1) + 'px,' + (y * 0.012).toFixed(1) + 'px)';
  });
  hero.addEventListener('mouseleave', function () {
    illustration.style.transform = 'translate(0,0)';
  });
})();
