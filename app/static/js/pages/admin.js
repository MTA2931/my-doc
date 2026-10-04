/**
 * Admin panel — dependency-free canvas charts (growth line chart)
 * drawn with theme-aware colors and DPR-correct scaling.
 */
(function () {
  'use strict';

  const { $ } = window.MyDoc;

  function cssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  }

  function drawGrowthChart(canvas) {
    let data;
    try {
      data = JSON.parse(canvas.dataset.chart || '{}');
    } catch (e) {
      return;
    }
    const labels = data.labels || [];
    const users = data.users || [];
    const docs = data.docs || [];
    if (!labels.length) return;

    const dpr = window.devicePixelRatio || 1;
    const cssWidth = canvas.clientWidth || canvas.parentElement.clientWidth || 600;
    const cssHeight = 220;
    canvas.width = cssWidth * dpr;
    canvas.height = cssHeight * dpr;
    canvas.style.height = `${cssHeight}px`;

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const padding = { top: 16, right: 12, bottom: 30, left: 32 };
    const plotW = cssWidth - padding.left - padding.right;
    const plotH = cssHeight - padding.top - padding.bottom;
    const maxVal = Math.max(4, ...users, ...docs);
    const gridColor = cssVar('--chart-grid', 'rgba(128,128,128,0.15)');
    const textColor = cssVar('--text-muted', '#888');
    const userColor = cssVar('--primary', '#4f46e5');
    const docColor = cssVar('--accent', '#0ea5e9');

    // Horizontal grid + y labels
    ctx.font = '11px system-ui, sans-serif';
    ctx.fillStyle = textColor;
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    const steps = 4;
    for (let i = 0; i <= steps; i += 1) {
      const y = padding.top + (plotH / steps) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(cssWidth - padding.right, y);
      ctx.stroke();
      const label = Math.round(maxVal - (maxVal / steps) * i);
      ctx.fillText(String(label), 4, y + 4);
    }

    // X labels (show every other to avoid crowding)
    ctx.textAlign = 'center';
    labels.forEach((label, i) => {
      if (i % 2 !== 0) return;
      const x = padding.left + (plotW / Math.max(1, labels.length - 1)) * i;
      ctx.fillText(label.slice(5), x, cssHeight - 10); // MM-DD
    });
    ctx.textAlign = 'left';

    function plotSeries(values, color) {
      if (!values.length) return;
      ctx.beginPath();
      values.forEach((v, i) => {
        const x = padding.left + (plotW / Math.max(1, values.length - 1)) * i;
        const y = padding.top + plotH - (v / maxVal) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.lineJoin = 'round';
      ctx.stroke();

      // Fill under the line with a soft gradient.
      const lastX = padding.left + plotW;
      const baseY = padding.top + plotH;
      ctx.lineTo(lastX, baseY);
      ctx.lineTo(padding.left, baseY);
      ctx.closePath();
      const gradient = ctx.createLinearGradient(0, padding.top, 0, baseY);
      gradient.addColorStop(0, color + '33');
      gradient.addColorStop(1, color + '00');
      ctx.fillStyle = gradient;
      ctx.fill();

      // Dots
      ctx.fillStyle = color;
      values.forEach((v, i) => {
        const x = padding.left + (plotW / Math.max(1, values.length - 1)) * i;
        const y = padding.top + plotH - (v / maxVal) * plotH;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    plotSeries(users, userColor);
    plotSeries(docs, docColor);
  }

  function initCharts() {
    const canvas = document.getElementById('growth-chart');
    if (!canvas || !canvas.getContext) return;
    drawGrowthChart(canvas);

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => drawGrowthChart(canvas), 180);
    });

    // Redraw when the theme changes so colors follow the palette.
    const observer = new MutationObserver(() => drawGrowthChart(canvas));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
  }

  document.addEventListener('DOMContentLoaded', initCharts);
})();
