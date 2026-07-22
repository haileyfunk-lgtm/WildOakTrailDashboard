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
  // Cost comparison calculator. Same math as hannybuyshouses.ca's version:
  // realtor commission 5%, closing costs 2%, repairs/updates 3%, staging
  // flat $3,000, holding costs 1%/mo x 3mo, traditional close ~90 days.
  // Cash offer is modeled at full slider value with $0 deductions and a
  // 10-day close, matching their calculator's framing exactly (it's a
  // "what you'd net" comparison tool, not a literal offer-price quote).
  var slider = document.getElementById('calc-slider');
  var valueDisplay = document.getElementById('calc-value-display');
  if (!slider || !valueDisplay) return;

  var fmt = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 });

  var els = {
    tCommission: document.getElementById('calc-t-commission'),
    tClosing: document.getElementById('calc-t-closing'),
    tRepairs: document.getElementById('calc-t-repairs'),
    tStaging: document.getElementById('calc-t-staging'),
    tHolding: document.getElementById('calc-t-holding'),
    tTotal: document.getElementById('calc-t-total'),
    tNet: document.getElementById('calc-t-net'),
    cOffer: document.getElementById('calc-c-offer'),
    cNet: document.getElementById('calc-c-net'),
    savings: document.getElementById('calc-savings')
  };

  function update() {
    var v = parseInt(slider.value, 10);
    valueDisplay.textContent = fmt.format(v);

    var commission = v * 0.05;
    var closing = v * 0.02;
    var repairs = v * 0.03;
    var staging = 3000;
    var holding = v * 0.01 * 3;
    var total = commission + closing + repairs + staging + holding;
    var netTraditional = v - total;
    var netCash = v;
    var savings = netCash - netTraditional;

    if (els.tCommission) els.tCommission.textContent = '-' + fmt.format(commission);
    if (els.tClosing) els.tClosing.textContent = '-' + fmt.format(closing);
    if (els.tRepairs) els.tRepairs.textContent = '-' + fmt.format(repairs);
    if (els.tStaging) els.tStaging.textContent = '-' + fmt.format(staging);
    if (els.tHolding) els.tHolding.textContent = '-' + fmt.format(holding);
    if (els.tTotal) els.tTotal.textContent = '-' + fmt.format(total);
    if (els.tNet) els.tNet.textContent = fmt.format(netTraditional);
    if (els.cOffer) els.cOffer.textContent = fmt.format(netCash);
    if (els.cNet) els.cNet.textContent = fmt.format(netCash);
    if (els.savings) els.savings.textContent = fmt.format(savings);

    var pct = (v - slider.min) / (slider.max - slider.min) * 100;
    slider.style.setProperty('--calc-fill', pct + '%');
  }

  slider.addEventListener('input', update);
  update();
})();

(function () {
  // Comparison table scroll-progress thumb (mobile only -- CSS hides the
  // track entirely above the 767px breakpoint). Thumb width reflects how
  // much of the table is visible at once; its position reflects actual
  // scroll progress, so it's a real indicator, not just a decoration.
  var area = document.getElementById('compare-scroll-area');
  var track = document.getElementById('compare-scrollbar-track');
  var thumb = document.getElementById('compare-scrollbar-thumb');
  if (!area || !track || !thumb) return;

  function updateThumb() {
    var scrollable = area.scrollWidth - area.clientWidth;
    var ratio = area.clientWidth / area.scrollWidth;
    var thumbWidthPx = track.clientWidth * ratio;
    thumb.style.width = thumbWidthPx + 'px';
    if (scrollable <= 0) {
      thumb.style.transform = 'translateX(0)';
      return;
    }
    var scrollRatio = area.scrollLeft / scrollable;
    var maxTranslate = track.clientWidth - thumbWidthPx;
    thumb.style.transform = 'translateX(' + (scrollRatio * maxTranslate) + 'px)';
  }

  area.addEventListener('scroll', updateThumb);
  window.addEventListener('resize', updateThumb);
  updateThumb();
})();
