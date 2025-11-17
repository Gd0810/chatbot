// function RedbotLoad(public_key) {
//     const div = document.getElementById('redbot-chat');
//     if (!div) return;

//     const iframe = document.createElement('iframe');
//     iframe.src = `http://localhost:8000/embed/widget/${public_key}?origin=${encodeURIComponent(window.location.origin)}`;
//     iframe.style.position = 'fixed';
//     iframe.style.bottom = '20px';
//     iframe.style.right = '20px';
//     iframe.style.width = '300px';
//     iframe.style.height = '400px';
//     iframe.style.border = 'none';
//     iframe.style.zIndex = '9999';
//     div.appendChild(iframe);
// }

// static/embed/bot.js (floating launcher + sliding chat iframe)
// (function () {
//   'use strict';

//   function getScriptOrigin() {
//     var s = document.currentScript ||
//             document.querySelector('script[src*="/static/embed/bot.js"]') ||
//             document.querySelector('script[src*="bot.js"]');
//     if (!s) return window.location.origin || 'http://127.0.0.1:8000';
//     try {
//       return new URL(s.getAttribute('src'), window.location.href).origin;
//     } catch (e) {
//       return window.location.origin || 'http://127.0.0.1:8000';
//     }
//   }

//   var SERVER_ORIGIN = getScriptOrigin();

//   function computeParentOrigin(originOverride) {
//     if (originOverride && typeof originOverride === 'string' && originOverride.trim() !== '') {
//       return originOverride;
//     }
//     var o = (window.location && window.location.origin) || '';
//     if (!o || o === 'null' || o === 'file://' || (typeof o === 'string' && o.indexOf('file:') === 0)) {
//       return SERVER_ORIGIN || 'http://127.0.0.1:8000';
//     }
//     return o;
//   }

//   function buildWidgetUrl(host, publicKey, parentOrigin) {
//     var t = Date.now();
//     return host.replace(/\/+$/, '') + '/embed/widget/' + encodeURIComponent(publicKey) +
//            '?origin=' + encodeURIComponent(parentOrigin) + '&v=' + t;
//   }

//   function injectStyles() {
//     if (document.getElementById('redbot-embed-styles')) return;
//     var css = `
//       .rb-launcher {
//         position: fixed; right: 20px; bottom: 20px; width: 56px; height: 56px;
//         border-radius: 50%; background: #2563eb; color: #fff; border: none;
//         display: flex; align-items: center; justify-content: center;
//         box-shadow: 0 10px 24px rgba(0,0,0,0.2); cursor: pointer; z-index: 2147483000;
//       }
//       .rb-launcher svg { width: 28px; height: 28px; }
//       .rb-wrapper {
//         position: fixed; right: 20px; bottom: 86px; width: 360px; max-width: calc(100vw - 24px);
//         height: 520px; border-radius: 12px; overflow: hidden; border: none;
//         box-shadow: 0 20px 40px rgba(0,0,0,0.2);
//         background: transparent; z-index: 2147483001;
//         opacity: 0; pointer-events: none; transform: translateY(10px);
//         transition: opacity 160ms ease, transform 160ms ease;
//       }
//       .rb-wrapper.open {
//         opacity: 1; pointer-events: auto; transform: translateY(0);
//       }
//       .rb-iframe { width: 100%; height: 100%; border: none; }
//       @media (max-width: 480px) {
//         .rb-wrapper { right: 12px; bottom: 76px; width: calc(100vw - 24px); height: 70vh; }
//         .rb-launcher { right: 12px; bottom: 12px; width: 52px; height: 52px; }
//       }
//     `;
//     var style = document.createElement('style');
//     style.id = 'redbot-embed-styles';
//     style.textContent = css;
//     document.head.appendChild(style);
//   }

//   function createLauncherBtn(primaryColor) {
//     var btn = document.createElement('button');
//     btn.className = 'rb-launcher';
//     if (primaryColor) btn.style.background = primaryColor;
//     btn.setAttribute('aria-label', 'Open chat');
//     btn.innerHTML = `
//       <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
//         <path d="M12 3C7.03 3 3 6.58 3 11c0 2.04.91 3.89 2.41 5.29-.08.79-.31 1.86-.98 3.08-.12.22-.07.5.12.67.19.17.47.2.69.08 1.6-.86 2.7-1.44 3.34-1.8.91.24 1.87.36 2.92.36 4.97 0 9-3.58 9-8s-4.03-7-9-7z"/>
//       </svg>`;
//     return btn;
//   }

//   function RedbotLoad(publicKeyOrOptions, maybeOptions) {
//     var publicKey = typeof publicKeyOrOptions === 'string'
//       ? publicKeyOrOptions
//       : (publicKeyOrOptions && publicKeyOrOptions.publicKey);

//     var opts = (typeof publicKeyOrOptions === 'string' ? (maybeOptions || {}) : (publicKeyOrOptions || {}));
//     var host = opts.host || SERVER_ORIGIN;
//     var originOverride = opts.originOverride || null;
//     var primaryColor = opts.primaryColor || null;
//     var openByDefault = !!opts.open;

//     if (!publicKey) {
//       var el = document.getElementById(opts.containerId || 'redbot-chat');
//       if (el && el.dataset && el.dataset.publicKey) {
//         publicKey = el.dataset.publicKey;
//       }
//     }
//     if (!publicKey) {
//       console.warn('[Redbot] Missing public key.');
//       return null;
//     }

//     injectStyles();

//     var parentOrigin = computeParentOrigin(originOverride);
//     var widgetUrl = buildWidgetUrl(host, publicKey, parentOrigin);

//     // Wrapper (iframe container)
//     var wrapper = document.createElement('div');
//     wrapper.className = 'rb-wrapper';
//     var iframe = document.createElement('iframe');
//     iframe.className = 'rb-iframe';
//     iframe.src = widgetUrl;
//     wrapper.appendChild(iframe);
//     document.body.appendChild(wrapper);

//     // Launcher
//     var launcher = createLauncherBtn(primaryColor);
//     document.body.appendChild(launcher);

//     function open() { wrapper.classList.add('open'); }
//     function close() { wrapper.classList.remove('open'); }
//     function toggle() { wrapper.classList.toggle('open'); }

//     launcher.addEventListener('click', toggle);

//     // Listen for minimize requests from iframe (optional)
//     window.addEventListener('message', function (evt) {
//       try {
//         if (!evt || !evt.data) return;
//         if (evt.data === 'redbot:close') close();
//         if (evt.data && evt.data.type === 'redbot:open') open();
//         if (evt.data && evt.data.type === 'redbot:toggle') toggle();
//       } catch (e) {}
//     });

//     if (openByDefault) open();

//     var controller = {
//       publicKey: publicKey,
//       open: open, close: close, toggle: toggle,
//       destroy: function () {
//         if (launcher && launcher.parentNode) launcher.parentNode.removeChild(launcher);
//         if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
//       }
//     };

//     window.Redbot = window.Redbot || { widgets: {} };
//     window.Redbot.widgets[publicKey] = controller;
//     return controller;
//   }

//   window.RedbotLoad = RedbotLoad;

//   // Auto-init
//   document.addEventListener('DOMContentLoaded', function () {
//     var el = document.getElementById('redbot-chat');
//     if (!el) return;
//     var pk = el.getAttribute('data-public-key');
//     if (!pk) return;
//     RedbotLoad({
//       publicKey: pk,
//       originOverride: el.getAttribute('data-origin-override') || null,
//       open: (el.getAttribute('data-open') || 'false') === 'true',
//       primaryColor: el.getAttribute('data-primary-color') || null
//     });
//   });
// })();


// // static/embed/bot.js
// (function () {
//   'use strict';

//   function getScriptOrigin() {
//     var s = document.currentScript ||
//             document.querySelector('script[src*="/static/embed/bot.js"]') ||
//             document.querySelector('script[src*="bot.js"]');
//     if (!s) return window.location.origin || 'http://127.0.0.1:8000';
//     try {
//       return new URL(s.getAttribute('src'), window.location.href).origin;
//     } catch (e) {
//       return window.location.origin || 'http://127.0.0.1:8000';
//     }
//   }

//   var SERVER_ORIGIN = getScriptOrigin();

//   function computeParentOrigin(originOverride) {
//     if (originOverride && typeof originOverride === 'string' && originOverride.trim() !== '') {
//       return originOverride;
//     }
//     var o = (window.location && window.location.origin) || '';
//     if (!o || o === 'null' || o === 'file://' || (typeof o === 'string' && o.indexOf('file:') === 0)) {
//       return SERVER_ORIGIN || 'http://127.0.0.1:8000';
//     }
//     return o;
//   }

//   function injectStyles() {
//     if (document.getElementById('rb-launcher-styles')) return;
//     var css = `
//       .rb-launcher {
//         position: fixed; right: 20px; bottom: 20px; width: 56px; height: 56px;
//         border-radius: 50%; border: none; color: #fff; background: var(--rb-launcher-bg, #2563eb);
//         display: inline-flex; align-items: center; justify-content: center;
//         box-shadow: 0 12px 28px rgba(0,0,0,0.25); cursor: pointer; z-index: 2147483000;
//         transition: transform .18s ease, box-shadow .18s ease, opacity .18s ease;
//       }
//       .rb-launcher:hover { transform: translateY(-1px) scale(1.02); box-shadow: 0 16px 36px rgba(0,0,0,0.28); }
//       .rb-launcher:active { transform: translateY(0) scale(0.98); }

//       .rb-launcher svg { width: 28px; height: 28px; }

//       .rb-wrapper {
//         position: fixed; right: 20px; bottom: 86px; width: 380px; max-width: calc(100vw - 24px);
//         height: 560px; border-radius: 16px; overflow: hidden; border: none; background: transparent;
//         box-shadow: 0 24px 48px rgba(0,0,0,0.25); z-index: 2147483001;
//         opacity: 0; pointer-events: none; transform: translateY(12px);
//         transition: opacity .22s ease, transform .22s ease;
//       }
//       .rb-wrapper.open { opacity: 1; pointer-events: auto; transform: translateY(0); }
//       .rb-iframe { width: 100%; height: 100%; border: none; }

//       @media (max-width: 480px) {
//         .rb-wrapper { right: 12px; bottom: 76px; width: calc(100vw - 24px); height: 70vh; }
//         .rb-launcher { right: 12px; bottom: 12px; width: 54px; height: 54px; }
//       }
//     `;
//     var style = document.createElement('style');
//     style.id = 'rb-launcher-styles';
//     style.textContent = css;
//     document.head.appendChild(style);
//   }

//   function buildWidgetUrl(host, publicKey, parentOrigin, themeHex) {
//     var t = Date.now();
//     var url = host.replace(/\/+$/, '') + '/embed/widget/' + encodeURIComponent(publicKey) +
//               '/?origin=' + encodeURIComponent(parentOrigin) + '&v=' + t;
//     if (themeHex && typeof themeHex === 'string' && themeHex.trim() !== '') {
//       var c = themeHex.trim();
//       url += '&theme=' + encodeURIComponent(c);
//     }
//     return url;
//   }

//   function createLauncher(color) {
//     var btn = document.createElement('button');
//     btn.className = 'rb-launcher';
//     if (color) btn.style.setProperty('--rb-launcher-bg', color);
//     btn.setAttribute('aria-label', 'Open chat');
//     btn.innerHTML = `
//       <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
//         <path d="M12 3C7.03 3 3 6.58 3 11c0 2.04.91 3.89 2.41 5.29-.08.79-.31 1.86-.98 3.08-.12.22-.07.5.12.67.19.17.47.2.69.08 1.6-.86 2.7-1.44 3.34-1.8.91.24 1.87.36 2.92.36 4.97 0 9-3.58 9-8s-4.03-7-9-7z"/>
//       </svg>
//     `;
//     return btn;
//   }

//   function RedbotLoad(publicKeyOrOptions, maybeOptions) {
//     var publicKey = typeof publicKeyOrOptions === 'string'
//       ? publicKeyOrOptions
//       : (publicKeyOrOptions && publicKeyOrOptions.publicKey);

//     var opts = (typeof publicKeyOrOptions === 'string' ? (maybeOptions || {}) : (publicKeyOrOptions || {}));

//     // Prefer placeholder if publicKey missing
//     if (!publicKey) {
//       var el = document.getElementById(opts.containerId || 'redbot-chat');
//       if (el && el.dataset && el.dataset.publicKey) {
//         publicKey = el.dataset.publicKey;
//         opts.primaryColor = opts.primaryColor || el.getAttribute('data-primary-color') || undefined;
//         opts.open = (el.getAttribute('data-open') || 'false') === 'true';
//         opts.originOverride = opts.originOverride || el.getAttribute('data-origin-override') || undefined;
//       }
//     }
//     if (!publicKey) {
//       console.warn('[Redbot] Missing public key.');
//       return null;
//     }

//     injectStyles();

//     var host = opts.host || SERVER_ORIGIN;
//     var parentOrigin = computeParentOrigin(opts.originOverride);
//     var theme = (opts.primaryColor || '').trim();
//     var widgetUrl = buildWidgetUrl(host, publicKey, parentOrigin, theme);

//     // Elements
//     var wrapper = document.createElement('div');
//     wrapper.className = 'rb-wrapper';
//     var iframe = document.createElement('iframe');
//     iframe.className = 'rb-iframe';
//     iframe.src = widgetUrl;
//     wrapper.appendChild(iframe);
//     document.body.appendChild(wrapper);

//     var launcher = createLauncher(theme || null);
//     document.body.appendChild(launcher);

//     // State persistence
//     var stateKey = 'rb_open_' + publicKey;
//     function saveOpenState(isOpen) {
//       try { localStorage.setItem(stateKey, isOpen ? '1' : '0'); } catch(e){}
//     }
//     function loadOpenState() {
//       try { return localStorage.getItem(stateKey) === '1'; } catch(e) { return false; }
//     }

//     function open() { wrapper.classList.add('open'); saveOpenState(true); }
//     function close() { wrapper.classList.remove('open'); saveOpenState(false); }
//     function toggle() { if (wrapper.classList.contains('open')) { close(); } else { open(); } }

//     launcher.addEventListener('click', toggle);

//     // Listen to iframe requests
//     window.addEventListener('message', function (evt) {
//       if (!evt || !evt.data) return;
//       var d = evt.data;
//       if (d === 'redbot:close') close();
//       if (d && d.type === 'redbot:open') open();
//       if (d && d.type === 'redbot:toggle') toggle();
//     });

//     // Initial open state
//     var savedOpen = loadOpenState();
//     if (typeof opts.open === 'boolean') {
//       if (opts.open) open(); else close();
//     } else if (savedOpen) {
//       open();
//     }

//     // Public controller
//     var controller = {
//       publicKey: publicKey,
//       open: open,
//       close: close,
//       toggle: toggle,
//       setTheme: function (hex) {
//         // Update launcher color and reload iframe with theme param
//         if (hex && typeof hex === 'string') {
//           launcher.style.setProperty('--rb-launcher-bg', hex);
//           var newUrl = buildWidgetUrl(host, publicKey, parentOrigin, hex);
//           iframe.src = newUrl;
//         }
//       },
//       destroy: function () {
//         if (launcher && launcher.parentNode) launcher.parentNode.removeChild(launcher);
//         if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
//       }
//     };

//     window.Redbot = window.Redbot || { widgets: {} };
//     window.Redbot.widgets[publicKey] = controller;
//     return controller;
//   }

//   window.RedbotLoad = RedbotLoad;

//   // Auto-init via placeholder
//   document.addEventListener('DOMContentLoaded', function () {
//     var el = document.getElementById('redbot-chat');
//     if (!el) return;
//     var pk = el.getAttribute('data-public-key');
//     if (!pk) return;
//     RedbotLoad({
//       publicKey: pk,
//       primaryColor: el.getAttribute('data-primary-color') || null,
//       originOverride: el.getAttribute('data-origin-override') || null,
//       open: (el.getAttribute('data-open') || 'false') === 'true'
//     });
//   });
// })();


// static/embed/bot.js
// static/embed/bot.js (updated for theme color, position, animation speed, persistence)
// static/embed/bot.js
// static/embed/bot.js
// static/embed/bot.js
(function () {
  'use strict';

  function getScriptOrigin() {
    var s = document.currentScript ||
            document.querySelector('script[src*="/static/embed/bot.js"]') ||
            document.querySelector('script[src*="bot.js"]');
    if (!s) return window.location.origin || 'http://127.0.0.1:8000';
    try {
      return new URL(s.getAttribute('src'), window.location.href).origin;
    } catch (e) {
      return window.location.origin || 'http://127.0.0.1:8000';
    }
  }

  var SERVER_ORIGIN = getScriptOrigin();

  function computeParentOrigin(originOverride) {
    if (originOverride && typeof originOverride === 'string' && originOverride.trim() !== '') {
      return originOverride;
    }
    var o = (window.location && window.location.origin) || '';
    if (!o || o === 'null' || o === 'file://' || (typeof o === 'string' && o.indexOf('file:') === 0)) {
      return SERVER_ORIGIN || 'http://127.0.0.1:8000';
    }
    return o;
  }

  function injectStyles() {
    if (document.getElementById('rb-launcher-styles')) return;
    var css = `
      .rb-launcher {
        position: fixed; right: 24px; bottom: 24px; width: 64px; height: 64px;
        border-radius: 50%; border: none; color: #fff; 
        background: var(--rb-launcher-bg, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
        display: inline-flex; align-items: center; justify-content: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15), 0 4px 8px rgba(0,0,0,0.1);
        cursor: pointer; z-index: 2147483000;
        transition: transform .25s cubic-bezier(0.34, 1.56, 0.64, 1), 
                    box-shadow .25s ease, 
                    opacity .2s ease;
        animation: rb-pulse 2s ease-in-out infinite;
      }
      
      @keyframes rb-pulse {
        0%, 100% { box-shadow: 0 8px 24px rgba(0,0,0,0.15), 0 4px 8px rgba(0,0,0,0.1); }
        50% { box-shadow: 0 8px 28px rgba(0,0,0,0.2), 0 4px 12px rgba(0,0,0,0.15), 0 0 0 8px rgba(102, 126, 234, 0.1); }
      }
      
      .rb-launcher:hover { 
        transform: translateY(-4px) scale(1.05); 
        box-shadow: 0 16px 40px rgba(0,0,0,0.25), 0 8px 16px rgba(0,0,0,0.15);
        animation: none;
      }
      
      .rb-launcher:active { 
        transform: translateY(-2px) scale(1.02); 
        box-shadow: 0 8px 20px rgba(0,0,0,0.2);
      }

      .rb-launcher svg { 
        width: 32px; height: 32px; 
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        transition: transform .2s ease;
      }
      
      .rb-launcher:hover svg {
        transform: scale(1.1) rotate(5deg);
      }

      .rb-wrapper {
        position: fixed; right: 24px; bottom: 100px; 
        width: 400px; max-width: calc(100vw - 32px);
        height: 600px; max-height: calc(100vh - 140px);
        border-radius: 20px; overflow: hidden; border: none; 
        background: #ffffff;
        box-shadow: 0 20px 60px rgba(0,0,0,0.2), 
                    0 8px 24px rgba(0,0,0,0.15),
                    0 0 0 1px rgba(0,0,0,0.05);
        z-index: 2147483001;
        opacity: 0; pointer-events: none; 
        transform: translateY(20px) scale(0.95);
        transform-origin: bottom right;
        transition: opacity .3s cubic-bezier(0.34, 1.56, 0.64, 1), 
                    transform .3s cubic-bezier(0.34, 1.56, 0.64, 1);
      }
      
      .rb-wrapper.open { 
        opacity: 1; 
        pointer-events: auto; 
        transform: translateY(0) scale(1); 
      }
      
      .rb-iframe { 
        width: 100%; 
        height: 100%; 
        border: none; 
        background: #fff;
      }

      @media (max-width: 640px) {
        .rb-wrapper { 
          right: 16px; bottom: 90px; 
          width: calc(100vw - 32px); 
          height: calc(100vh - 120px);
          border-radius: 16px;
        }
        .rb-launcher { 
          right: 16px; bottom: 16px; 
          width: 56px; height: 56px; 
        }
        .rb-launcher svg { width: 28px; height: 28px; }
      }

      @media (prefers-reduced-motion: reduce) {
        .rb-launcher, .rb-wrapper { transition: none; animation: none; }
      }
    `;
    var style = document.createElement('style');
    style.id = 'rb-launcher-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function buildWidgetUrl(host, publicKey, parentOrigin, themeHex, fontFamily, fontSize, welcomeMsg, soundEnabled, bgColor, animSpeed, widgetPos) {
    var t = Date.now();
    var url = host.replace(/\/+$/, '') + '/embed/widget/' + encodeURIComponent(publicKey) +
              '/?origin=' + encodeURIComponent(parentOrigin) + '&v=' + t;
    
    if (themeHex && typeof themeHex === 'string' && themeHex.trim() !== '') {
      url += '&theme=' + encodeURIComponent(themeHex.trim());
    }
    if (bgColor && typeof bgColor === 'string' && bgColor.trim() !== '') {
      url += '&bgcolor=' + encodeURIComponent(bgColor.trim());
    }
    if (fontFamily && typeof fontFamily === 'string' && fontFamily.trim() !== '') {
      url += '&font=' + encodeURIComponent(fontFamily.trim());
    }
    if (fontSize && (typeof fontSize === 'number' || typeof fontSize === 'string')) {
      url += '&fontsize=' + encodeURIComponent(String(fontSize));
    }
    if (welcomeMsg && typeof welcomeMsg === 'string' && welcomeMsg.trim() !== '') {
      url += '&welcome=' + encodeURIComponent(welcomeMsg.trim());
    }
    if (typeof soundEnabled === 'boolean') {
      url += '&sound=' + (soundEnabled ? '1' : '0');
    }
    if (animSpeed && typeof animSpeed === 'string') {
      url += '&animspeed=' + encodeURIComponent(animSpeed);
    }
    if (widgetPos && typeof widgetPos === 'string') {
      url += '&pos=' + encodeURIComponent(widgetPos);
    }
    
    return url;
  }

  function createLauncher(color) {
    var btn = document.createElement('button');
    btn.className = 'rb-launcher';
    btn.setAttribute('aria-label', 'Open chat');
    btn.setAttribute('role', 'button');
    
    if (color) {
      // Support both solid colors and gradients
      if (color.includes('linear-gradient') || color.includes('radial-gradient')) {
        btn.style.background = color;
      } else {
        btn.style.background = 'linear-gradient(135deg, ' + color + ' 0%, ' + adjustColorBrightness(color, -20) + ' 100%)';
      }
    }
    
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        <circle cx="12" cy="10" r="1.5"/>
        <circle cx="8" cy="10" r="1.5"/>
        <circle cx="16" cy="10" r="1.5"/>
      </svg>
    `;
    return btn;
  }

  function adjustColorBrightness(hex, percent) {
    // Simple color adjustment for gradient
    hex = hex.replace('#', '');
    var r = parseInt(hex.substring(0, 2), 16);
    var g = parseInt(hex.substring(2, 4), 16);
    var b = parseInt(hex.substring(4, 6), 16);
    
    r = Math.max(0, Math.min(255, r + (r * percent / 100)));
    g = Math.max(0, Math.min(255, g + (g * percent / 100)));
    b = Math.max(0, Math.min(255, b + (b * percent / 100)));
    
    return '#' + 
      ('0' + Math.round(r).toString(16)).slice(-2) +
      ('0' + Math.round(g).toString(16)).slice(-2) +
      ('0' + Math.round(b).toString(16)).slice(-2);
  }

  function RedbotLoad(publicKeyOrOptions, maybeOptions) {
    var publicKey = typeof publicKeyOrOptions === 'string'
      ? publicKeyOrOptions
      : (publicKeyOrOptions && publicKeyOrOptions.publicKey);

    var opts = (typeof publicKeyOrOptions === 'string' ? (maybeOptions || {}) : (publicKeyOrOptions || {}));

    // Prefer placeholder if publicKey missing
    if (!publicKey) {
      var el = document.getElementById(opts.containerId || 'redbot-chat');
      if (el && el.dataset && el.dataset.publicKey) {
        publicKey = el.dataset.publicKey;
      }
    }
    if (!publicKey) {
      console.warn('[Redbot] Missing public key.');
      return null;
    }

    // Fetch config from server if not already in opts
    // This allows user's page to have just: <div id="redbot-chat" data-public-key="..."></div>
    // and <script>RedbotLoad('...');</script>
    if (!opts.widgetPosition) {
      try {
        fetch('/embed/config/' + encodeURIComponent(publicKey) + '/')
          .then(function(r) { return r.ok ? r.json() : null; })
          .then(function(cfg) {
            if (!cfg) return;
            try { console.log('[Redbot] Fetched config from server:', cfg); } catch (e) {}
            opts.primaryColor = opts.primaryColor || cfg.primary_color;
            opts.bgColor = opts.bgColor || cfg.bg_color;
            opts.fontFamily = opts.fontFamily || cfg.font_family;
            opts.fontSize = opts.fontSize || cfg.font_size;
            opts.welcomeMessage = opts.welcomeMessage || cfg.welcome_message;
            if (typeof opts.soundEnabled === 'undefined') opts.soundEnabled = cfg.sound_enabled;
            opts.animationSpeed = opts.animationSpeed || cfg.animation_speed;
            opts.widgetPosition = opts.widgetPosition || cfg.widget_position;
            _doLoad(publicKey, opts);
          })
          .catch(function(e) {
            try { console.warn('[Redbot] Config fetch failed:', e); } catch (e2) {}
            _doLoad(publicKey, opts);
          });
      } catch (e) {
        _doLoad(publicKey, opts);
      }
    } else {
      _doLoad(publicKey, opts);
    }
  }

  function _doLoad(publicKey, opts) {
    injectStyles();

    var host = opts.host || SERVER_ORIGIN;
    var parentOrigin = computeParentOrigin(opts.originOverride);
    var theme = (opts.primaryColor || '').trim();
    var bgColor = (opts.bgColor || '').trim();
    var fontFamily = (opts.fontFamily || '').trim();
    var fontSize = opts.fontSize;
    var welcomeMsg = (opts.welcomeMessage || '').trim();
    var soundEnabled = opts.soundEnabled;
    var animSpeed = (opts.animationSpeed || '').trim();
  // Normalize widget position into a small set of supported values
  var rawPos = (opts.widgetPosition || 'bottom-right').toString().trim().toLowerCase();
  var widgetPos = 'bottom-right';
  if (rawPos === 'left' || rawPos === 'bottom-left' || rawPos === 'left-bottom' || rawPos === 'left-bottom') widgetPos = 'bottom-left';
  else if (rawPos === 'right' || rawPos === 'bottom-right' || rawPos === 'right-bottom') widgetPos = 'bottom-right';
  else if (rawPos === 'top-left' || rawPos === 'left-top') widgetPos = 'top-left';
  else if (rawPos === 'top-right' || rawPos === 'right-top') widgetPos = 'top-right';
  else widgetPos = rawPos || 'bottom-right';
  // debug: report what we received and the normalized position
  try { console.log('[Redbot] init: raw widget position ->', rawPos, 'normalized ->', widgetPos); } catch (e) {}
    
    var widgetUrl = buildWidgetUrl(host, publicKey, parentOrigin, theme, fontFamily, fontSize, welcomeMsg, soundEnabled, bgColor, animSpeed, widgetPos);

    // Elements
    var wrapper = document.createElement('div');
    wrapper.className = 'rb-wrapper';
    wrapper.setAttribute('role', 'dialog');
    wrapper.setAttribute('aria-label', 'Chat window');
    
    // Apply widget position styling (supports bottom-left, bottom-right, top-left, top-right)
    function applyPosition(pos) {
      try { console.log('[Redbot] applyPosition called with pos =', pos); } catch (e) {}
      // reset a few possible styles
      wrapper.style.left = wrapper.style.right = wrapper.style.top = wrapper.style.bottom = '';
      launcher.style.left = launcher.style.right = launcher.style.top = launcher.style.bottom = '';

      if (pos === 'bottom-left') {
        wrapper.style.right = 'auto';
        wrapper.style.left = '24px';
        wrapper.style.bottom = '100px';
        wrapper.style.transformOrigin = 'bottom left';

        launcher.style.right = 'auto';
        launcher.style.left = '24px';
        launcher.style.bottom = '24px';
      } else if (pos === 'top-left') {
        wrapper.style.bottom = 'auto';
        wrapper.style.top = '24px';
        wrapper.style.left = '24px';
        wrapper.style.transformOrigin = 'top left';

        launcher.style.bottom = 'auto';
        launcher.style.top = '24px';
        launcher.style.left = '24px';
      } else if (pos === 'top-right') {
        wrapper.style.bottom = 'auto';
        wrapper.style.top = '24px';
        wrapper.style.right = '24px';
        wrapper.style.transformOrigin = 'top right';

        launcher.style.bottom = 'auto';
        launcher.style.top = '24px';
        launcher.style.right = '24px';
      } else { // bottom-right (default)
        wrapper.style.left = 'auto';
        wrapper.style.right = '24px';
        wrapper.style.bottom = '100px';
        wrapper.style.transformOrigin = 'bottom right';

        launcher.style.left = 'auto';
        launcher.style.right = '24px';
        launcher.style.bottom = '24px';
      }

      // small-screen override: keep launcher near edge but wrapper full width
      try {
        if (window.innerWidth <= 640) {
          wrapper.style.left = '16px';
          wrapper.style.right = '16px';
          wrapper.style.bottom = '90px';
          wrapper.style.width = 'calc(100vw - 32px)';
        }
      } catch (e) {}
  }
    
    var iframe = document.createElement('iframe');
    iframe.className = 'rb-iframe';
    iframe.src = widgetUrl;
    iframe.title = 'Chat widget';
    wrapper.appendChild(iframe);
    document.body.appendChild(wrapper);

    var launcher = createLauncher(theme || null);
    
  // Apply positions for launcher and wrapper
  try { if (typeof applyPosition === 'function') { applyPosition(widgetPos); console.log('[Redbot] applied initial widgetPos =', widgetPos); } } catch (e) {}
    document.body.appendChild(launcher);

    // State persistence
    var stateKey = 'rb_open_' + publicKey;
    function saveOpenState(isOpen) {
      try { localStorage.setItem(stateKey, isOpen ? '1' : '0'); } catch(e){}
    }
    function loadOpenState() {
      try { return localStorage.getItem(stateKey) === '1'; } catch(e) { return false; }
    }

    function open() { 
      wrapper.classList.add('open'); 
      saveOpenState(true);
      launcher.setAttribute('aria-expanded', 'true');
    }
    
    function close() { 
      wrapper.classList.remove('open'); 
      saveOpenState(false);
      launcher.setAttribute('aria-expanded', 'false');
    }
    
    function toggle() { 
      if (wrapper.classList.contains('open')) { 
        close(); 
      } else { 
        open(); 
      } 
    }

    launcher.addEventListener('click', toggle);

    // Listen to iframe requests
    window.addEventListener('message', function (evt) {
      if (!evt || !evt.data) return;
      var d = evt.data;
      if (d === 'redbot:close') close();
      if (d && d.type === 'redbot:open') open();
      if (d && d.type === 'redbot:toggle') toggle();
    });

    // Initial open state
    var savedOpen = loadOpenState();
    if (typeof opts.open === 'boolean') {
      if (opts.open) open(); else close();
    } else if (savedOpen) {
      open();
    }

    // Public controller
    var controller = {
      publicKey: publicKey,
      open: open,
      close: close,
      toggle: toggle,
  setTheme: function (hex, fontFam, fontSz, welcome, sound, bg, anim, pos) {
        // Update launcher color and reload iframe with all theme params
        if (hex && typeof hex === 'string') {
          if (hex.includes('gradient')) {
            launcher.style.background = hex;
          } else {
            launcher.style.background = 'linear-gradient(135deg, ' + hex + ' 0%, ' + adjustColorBrightness(hex, -20) + ' 100%)';
          }
        }
        
        // Update position if specified (normalize synonyms)
        try {
          var p = (pos || '').toString().trim().toLowerCase();
          if (p === 'left' || p === 'bottom-left' || p === 'left-bottom') p = 'bottom-left';
          else if (p === 'right' || p === 'bottom-right' || p === 'right-bottom') p = 'bottom-right';
          else if (p === 'top-left' || p === 'left-top') p = 'top-left';
          else if (p === 'top-right' || p === 'right-top') p = 'top-right';
          try { console.log('[Redbot] setTheme received pos ->', pos, 'normalized ->', p); } catch (e) {}
          if (typeof applyPosition === 'function') applyPosition(p);
        } catch (e) {}
        
        var newUrl = buildWidgetUrl(host, publicKey, parentOrigin, hex, fontFam, fontSz, welcome, sound, bg, anim, pos);
        iframe.src = newUrl;
      },
      destroy: function () {
        if (launcher && launcher.parentNode) launcher.parentNode.removeChild(launcher);
        if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
      }
    };

    window.Redbot = window.Redbot || { widgets: {} };
    window.Redbot.widgets[publicKey] = controller;
    return controller;
  }

  window.RedbotLoad = RedbotLoad;

  // Auto-init via placeholder
  document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('redbot-chat');
    if (!el) return;
    var pk = el.getAttribute('data-public-key');
    if (!pk) return;
    RedbotLoad({
      publicKey: pk,
      primaryColor: el.getAttribute('data-primary-color') || null,
      bgColor: el.getAttribute('data-bg-color') || null,
      fontFamily: el.getAttribute('data-font-family') || null,
      fontSize: el.getAttribute('data-font-size') || null,
      welcomeMessage: el.getAttribute('data-welcome-message') || null,
      soundEnabled: el.hasAttribute('data-sound-enabled') ? el.getAttribute('data-sound-enabled') === 'true' : null,
      animationSpeed: el.getAttribute('data-animation-speed') || null,
      widgetPosition: el.getAttribute('data-widget-position') || null,
      originOverride: el.getAttribute('data-origin-override') || null,
      open: (el.getAttribute('data-open') || 'false') === 'true'
    });
  });
})();