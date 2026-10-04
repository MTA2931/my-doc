/**
 * MyDoc local syntax highlighter — dependency-free, regex-based.
 * Highlights <pre><code class="language-xxx"> blocks after render.
 * Supported: python, js/ts, java, c/cpp/csharp, go, rust, bash, json,
 * yaml, sql, css, xml/html.
 */
(function () {
  'use strict';

  const KEYWORDS = {
    python:
      'and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|match|case',
    javascript:
      'await|break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|function|if|import|in|instanceof|let|new|of|return|static|super|switch|this|throw|try|typeof|var|void|while|with|yield|async|get|set',
    typescript:
      'await|break|case|catch|class|const|continue|debugger|default|delete|do|else|enum|export|extends|finally|for|function|if|implements|import|in|instanceof|interface|let|new|of|private|protected|public|readonly|return|static|super|switch|this|throw|try|type|typeof|var|void|while|with|yield|async|namespace|declare|as',
    java:
      'abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|extends|final|finally|float|for|goto|if|implements|import|instanceof|int|interface|long|native|new|package|private|protected|public|return|short|static|strictfp|super|switch|synchronized|this|throw|throws|transient|try|void|volatile|while|var|record',
    c:
      'auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|restrict|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while',
    cpp:
      'alignas|and|asm|auto|bool|break|case|catch|char|class|const|constexpr|continue|default|delete|do|double|else|enum|explicit|extern|false|float|for|friend|goto|if|inline|int|long|namespace|new|noexcept|not|nullptr|operator|or|private|protected|public|register|return|short|signed|sizeof|static|struct|switch|template|this|throw|true|try|typedef|typename|union|unsigned|using|virtual|void|volatile|while',
    csharp:
      'abstract|as|base|bool|break|byte|case|catch|char|checked|class|const|continue|decimal|default|delegate|do|double|else|enum|event|explicit|extern|false|finally|fixed|float|for|foreach|goto|if|implicit|in|int|interface|internal|is|lock|long|namespace|new|null|object|operator|out|override|params|private|protected|public|readonly|ref|return|sbyte|sealed|short|sizeof|stackalloc|static|string|struct|switch|this|throw|true|try|typeof|uint|ulong|unchecked|unsafe|ushort|using|virtual|void|volatile|while|var',
    go:
      'break|case|chan|const|continue|default|defer|else|fallthrough|for|func|go|goto|if|import|interface|map|package|range|return|select|struct|switch|type|var|nil|true|false',
    rust:
      'as|async|await|break|const|continue|crate|dyn|else|enum|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while',
    bash:
      'if|then|else|elif|fi|for|in|do|done|while|until|case|esac|function|select|time|break|continue|return|exit|local|export|declare|readonly|source|alias|unset|set|shift|trap|eval|exec|test|echo|sudo|curl|wget|git|npm|pip|python|docker',
    sql:
      'SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|DROP|ALTER|ADD|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|DEFAULT|INDEX|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|AS|AND|OR|IN|LIKE|BETWEEN|DISTINCT|COUNT|SUM|AVG|MAX|MIN|UNION|ALL|EXISTS|CASE|WHEN|THEN|ELSE|END',
    yaml: 'true|false|null|yes|no|on|off',
    json: 'true|false|null',
    css: '',
    xml: '',
  };

  const ALIASES = {
    javascript: ['javascript', 'js', 'jsx', 'mjs'],
    typescript: ['typescript', 'ts', 'tsx'],
    python: ['python', 'py'],
    java: ['java'],
    c: ['c', 'h'],
    cpp: ['cpp', 'c++', 'cc', 'hpp'],
    csharp: ['csharp', 'cs', 'c#'],
    go: ['go', 'golang'],
    rust: ['rust', 'rs'],
    bash: ['bash', 'sh', 'shell', 'zsh', 'console', 'terminal'],
    sql: ['sql', 'pgsql', 'mysql'],
    yaml: ['yaml', 'yml'],
    json: ['json'],
    css: ['css'],
    xml: ['xml', 'html', 'htm', 'svg'],
    plaintext: ['plaintext', 'text', 'txt'],
  };

  function langKey(alias) {
    const a = String(alias || '').toLowerCase();
    for (const [key, names] of Object.entries(ALIASES)) {
      if (names.includes(a)) return key;
    }
    return null;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /** Build ordered rule list for a language (all patterns non-capturing). */
  function rulesFor(lang) {
    const rules = [];
    const words = KEYWORDS[lang];
    const hasSlashSlash = ['javascript', 'typescript', 'go', 'rust', 'c', 'cpp',
                           'csharp', 'java', 'css', 'sql'].includes(lang);

    if (['bash', 'python', 'yaml'].includes(lang)) {
      rules.push({ re: '#[^\\n]*', cls: 'tok-com' });
    }
    if (hasSlashSlash) {
      rules.push({ re: '\\/\\/[^\\n]*', cls: 'tok-com' });
    }
    if (['javascript', 'typescript', 'go', 'rust', 'c', 'cpp', 'csharp',
         'java', 'css', 'sql'].includes(lang)) {
      rules.push({ re: '\\/\\*[\\s\\S]*?\\*\\/', cls: 'tok-com' });
    }
    if (lang === 'xml') {
      rules.push({ re: '&lt;!--[\\s\\S]*?--&gt;', cls: 'tok-com' });
      rules.push({ re: '<\\?[\\s\\S]*?\\?>', cls: 'tok-com' });
    }

    // Strings before keywords so reserved words inside strings stay plain.
    rules.push({ re: '`(?:\\\\.|[^`\\\\])*`', cls: 'tok-str' });
    rules.push({ re: '"(?:\\\\.|[^"\\\\\\n])*"', cls: 'tok-str' });
    rules.push({ re: "'(?:\\\\.|[^'\\\\\\n])*'", cls: 'tok-str' });

    if (['python', 'java', 'csharp'].includes(lang)) {
      rules.push({ re: '@[A-Za-z_][\\w.]*', cls: 'tok-meta' });
    }

    rules.push({
      re: '\\b0[xX][0-9a-fA-F]+\\b|\\b\\d[\\d_]*(?:\\.\\d+)?(?:[eE][+-]?\\d+)?\\b',
      cls: 'tok-num',
    });

    if (words) {
      rules.push({ re: `\\b(?:${words})\\b`, cls: 'tok-kw' });
    }
    if (lang === 'python') {
      rules.push({ re: '\\b(?:True|False|None)\\b', cls: 'tok-kw' });
    }
    if (['json', 'yaml', 'javascript', 'typescript'].includes(lang)) {
      rules.push({ re: '\\b(?:true|false|null|undefined)\\b', cls: 'tok-kw' });
    }

    rules.push({ re: '\\b[A-Za-z_]\\w*(?=\\s*\\()', cls: 'tok-fn' });
    rules.push({ re: '\\b[A-Z][A-Za-z0-9_]*\\b', cls: 'tok-type' });
    return rules;
  }

  function highlightCode(code, lang) {
    const key = langKey(lang);
    if (!key || key === 'plaintext') return escapeHtml(code);

    const rules = rulesFor(key);
    const combined = new RegExp(rules.map((r) => `(${r.re})`).join('|'), 'g');

    // Replace matches with placeholders first so they never get re-scanned.
    const tokens = [];
    let text = String(code).replace(combined, (match, ...groups) => {
      let cls = 'tok-plain';
      for (let g = 0; g < groups.length - 1; g += 1) {
        if (groups[g] !== undefined) {
          cls = rules[g].cls;
          break;
        }
      }
      tokens.push(`<span class="${cls}">${escapeHtml(match)}</span>`);
      return `\u0001${tokens.length - 1}\u0001`;
    });

    text = escapeHtml(text);
    text = text.replace(/\u0001(\d+)\u0001/g, (_, i) => tokens[Number(i)]);
    return text;
  }

  function highlightAll(root) {
    (root || document).querySelectorAll('pre > code[class*="language-"]').forEach((el) => {
      if (el.dataset.highlighted === '1') return;
      const match = (el.className || '').match(/language-([\w+#-]+)/);
      const lang = match ? match[1] : 'plaintext';
      el.innerHTML = highlightCode(el.textContent, lang);
      el.dataset.highlighted = '1';
      const pre = el.parentElement;
      if (pre && !pre.dataset.lang) pre.dataset.lang = lang;
    });
  }

  document.addEventListener('DOMContentLoaded', () => highlightAll(document));

  window.MyDocHighlight = { highlightCode, highlightAll, escapeHtml };
})();

