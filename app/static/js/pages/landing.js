/**
 * MyDoc landing page — mouse-driven parallax depth for the 3D hero.
 * Disabled automatically when the user prefers reduced motion.
 */
(function () {
  'use strict';

  const hero = document.getElementById('hero');
  if (!hero) return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const scene = hero.querySelector('.stage-scene');
  const layers = Array.from(hero.querySelectorAll('[data-parallax]'));

  function onMove(event) {
    if (reduced.matches) return;
    const rect = hero.getBoundingClientRect();
    // Normalized [-1, 1] offsets from the hero centre.
    const px = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const py = ((event.clientY - rect.top) / rect.height) * 2 - 1;

    if (scene) {
      scene.style.setProperty('--px', px.toFixed(3));
      scene.style.setProperty('--py', py.toFixed(3));
    }
    layers.forEach((layer) => {
      const depth = Number(layer.getAttribute('data-parallax')) || 0.5;
      layer.style.transform =
        `translate3d(${(-px * 14 * depth).toFixed(1)}px, ` +
        `${(-py * 10 * depth).toFixed(1)}px, 0)`;
    });
  }

  function onLeave() {
    if (scene) {
      scene.style.setProperty('--px', '0');
      scene.style.setProperty('--py', '0');
    }
    layers.forEach((layer) => { layer.style.transform = ''; });
  }

  // Pointer devices only — touch would fight with scrolling.
  if (window.matchMedia('(pointer: fine)').matches && !reduced.matches) {
    hero.addEventListener('mousemove', onMove, { passive: true });
    hero.addEventListener('mouseleave', onLeave);
  }
})();
