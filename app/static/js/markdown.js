/**
 * MyDoc client-side Markdown renderer — used for live editor preview.
 *
 * Security note: ALL raw HTML in the source is escaped, so the preview can
 * never execute scripts. The authoritative, bleach-sanitized HTML is rendered
 * server-side when a document is saved (app/services/markdown_service.py).
 */
(function () {
  'use strict';

  const { escapeHtml } = window.MyDoc;

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  // ------------------------------------------------------------- inline
  function renderInline(text) {
    let out = text;

    // Inline code first so its contents are not processed further.
    const codeSpans = [];
    out = out.replace(/`([^`\n]+)`/g, (_, code) => {
      codeSpans.push(`<code>${code}</code>`);
      return `\u0000${codeSpans.length - 1}\u0000`;
    });

    // Images before links: ![alt](src)
    out = out.replace(
      /!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g,
      (_, alt, src, title) =>
        `<img src="${escapeAttr(src)}" alt="${escapeAttr(alt)}"` +
        (title ? ` title="${escapeAttr(title)}"` : '') +
        ' loading="lazy">'
    );

    // Links: [label](href)
    out = out.replace(
      /\[([^\]]+)\]\(([^)\s]+)\)/g,
      (_, label, href) => {
        const safe = /^(https?:|mailto:|\/|#)/i.test(href) ? href : '#';
        const external = /^https?:/i.test(safe);
        return (
          `<a href="${escapeAttr(safe)}"` +
          (external ? ' target="_blank" rel="noopener noreferrer"' : '') +
          `>${label}</a>`
        );
      }
    );

    // Bold, italic, strike, highlight
    out = out.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    out = out.replace(/(^|[\s(])_([^_\n]+)_/g, '$1<em>$2</em>');
    out = out.replace(/~~([^~]+)~~/g, '<del>$1</del>');
    out = out.replace(/==([^=]+)==/g, '<mark>$1</mark>');

    // Restore code spans
    out = out.replace(/\u0000(\d+)\u0000/g, (_, i) => codeSpans[Number(i)]);
    return out;
  }

  // -------------------------------------------------------------- blocks
  function isTableRow(line) {
    return /^\s*\|.*\|\s*$/.test(line);
  }

  function splitRow(line) {
    return line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim());
  }

  function renderMarkdown(source) {
    if (!source) return '';
    const lines = escapeHtml(source).split('\n');
    const html = [];
    let i = 0;
    let para = [];

    const flushPara = () => {
      if (para.length) {
        html.push(`<p>${renderInline(para.join('<br>'))}</p>`);
        para = [];
      }
    };

    while (i < lines.length) {
      const line = lines[i];

      // Fenced code block
      const fence = line.match(/^```(\w*)\s*$/);
      if (fence) {
        flushPara();
        const lang = fence[1] || 'plaintext';
        const buf = [];
        i += 1;
        while (i < lines.length && !/^```\s*$/.test(lines[i])) {
          buf.push(lines[i]);
          i += 1;
        }
        i += 1; // closing fence (or EOF)
        html.push(
          `<pre><code class="language-${escapeAttr(lang)}" data-lang="${escapeAttr(lang)}">` +
          `${buf.join('\n')}</code></pre>`
        );
        continue;
      }

      // Heading
      const heading = line.match(/^(#{1,6})\s+(.*)$/);
      if (heading) {
        flushPara();
        const level = heading[1].length;
        html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        i += 1;
        continue;
      }

      // Horizontal rule
      if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        flushPara();
        html.push('<hr>');
        i += 1;
        continue;
      }

      // Table
      if (isTableRow(line) && i + 1 < lines.length &&
          /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        flushPara();
        const head = splitRow(line);
        i += 2;
        const rows = [];
        while (i < lines.length && isTableRow(lines[i])) {
          rows.push(splitRow(lines[i]));
          i += 1;
        }
        let table = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
        head.forEach((h) => { table += `<th>${renderInline(h)}</th>`; });
        table += '</tr></thead><tbody>';
        rows.forEach((r) => {
          table += '<tr>';
          head.forEach((_, idx) => { table += `<td>${renderInline(r[idx] || '')}</td>`; });
          table += '</tr>';
        });
        table += '</tbody></table></div>';
        html.push(table);
        continue;
      }

      // Blockquote
      if (/^&gt;\s?/.test(line)) {
        flushPara();
        const buf = [];
        while (i < lines.length && /^&gt;\s?/.test(lines[i])) {
          buf.push(lines[i].replace(/^&gt;\s?/, ''));
          i += 1;
        }
        html.push(`<blockquote>${renderMarkdown(buf.join('\n'))}</blockquote>`);
        continue;
      }

      // Lists (unordered / ordered / task items)
      const listMatch = line.match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
      if (listMatch) {
        flushPara();
        const ordered = /\d+\./.test(listMatch[2]);
        const items = [];
        while (i < lines.length) {
          const m = lines[i].match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
          if (!m) break;
          items.push(m[3]);
          i += 1;
        }
        const tag = ordered ? 'ol' : 'ul';
        let list = `<${tag}>`;
        items.forEach((item) => {
          const task = item.match(/^\[( |x)\]\s+(.*)$/i);
          if (task) {
            const checked = task[1].toLowerCase() === 'x';
            list +=
              '<li class="md-task">' +
              `<input type="checkbox" disabled${checked ? ' checked' : ''}> ` +
              `${renderInline(task[2])}</li>`;
          } else {
            list += `<li>${renderInline(item)}</li>`;
          }
        });
        list += `</${tag}>`;
        html.push(list);
        continue;
      }

      // Blank line ends a paragraph
      if (!line.trim()) {
        flushPara();
        i += 1;
        continue;
      }

      para.push(line);
      i += 1;
    }

    flushPara();
    return html.join('\n');
  }

  window.MyDocMarkdown = { render: renderMarkdown };
})();

