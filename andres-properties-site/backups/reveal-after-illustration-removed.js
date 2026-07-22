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
