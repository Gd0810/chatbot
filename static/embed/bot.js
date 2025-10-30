// (function () {
//   'use strict';

//   // Find the script origin so the widget loads from the same host that served this file.
//   function getScriptOrigin() {
//     var s = document.currentScript ||
//             document.querySelector('script[src*="/static/embed/bot.js"]') ||
//             document.querySelector('script[src*="bot.js"]');
//     try {
//       return new URL(s.src).origin;
//     } catch (e) {
//       return 'http://localhost:8000';
//     }
//   }

//   var SERVER_ORIGIN = getScriptOrigin();

//   function computeParentOrigin(originOverride) {
//     var o = window.location.origin;
//     if (!o || o === 'null') {
//       // file:// pages report "null" origin; use override or a sane dev default
//       return originOverride || 'http://localhost:5500';
//     }
//     return o;
//   }

//   function normalizeOptions(opts) {
//     opts = opts || {};
//     return {
//       host: opts.host || SERVER_ORIGIN,              // Django host serving the widget
//       originOverride: opts.originOverride || null,   // For file:// testing
//       position: opts.position || 'bottom-right',     // bottom-right | bottom-left | inline
//       width: String(opts.width || 360),              // px
//       height: String(opts.height || 520),            // px
//       zIndex: String(opts.zIndex || 999999),
//       open: opts.open !== false,                     // true by default
//       showLauncher: opts.showLauncher === true,      // optional bubble launcher
//       launcherText: opts.launcherText || 'Chat',
//       containerId: opts.containerId || 'redbot-chat' // placeholder div id
//     };
//   }

//   function createStyles() {
//     if (document.getElementById('redbot-embed-styles')) return;
//     var css = `
//       .redbot-wrapper { position: fixed; bottom: 20px; right: 20px; }
//       .redbot-wrapper.left { left: 20px; right: auto; }
//       .redbot-iframe { border: none; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
//       .redbot-launcher {
//         position: fixed; bottom: 20px; right: 20px;
//         background: #2563eb; color: #fff; border: none; border-radius: 9999px;
//         padding: 12px 16px; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,0.15);
//         font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; font-size: 14px;
//       }
//       .redbot-launcher.left { left: 20px; right: auto; }
//     `;
//     var el = document.createElement('style');
//     el.id = 'redbot-embed-styles';
//     el.textContent = css;
//     document.head.appendChild(el);
//   }

//   function buildWidgetUrl(host, publicKey, parentOrigin) {
//     var t = Date.now(); // bust cache when needed
//     return host.replace(/\/+$/, '') + '/embed/widget/' + encodeURIComponent(publicKey) +
//            '?origin=' + encodeURIComponent(parentOrigin) + '&v=' + t;
//   }

//   function createWrapper(opts) {
//     var wrapper = document.createElement('div');
//     wrapper.className = 'redbot-wrapper' + (opts.position === 'bottom-left' ? ' left' : '');
//     wrapper.style.zIndex = opts.zIndex;
//     wrapper.style.display = opts.open ? 'block' : 'none';
//     return wrapper;
//   }

//   function createIframe(url, opts) {
//     var iframe = document.createElement('iframe');
//     iframe.src = url;
//     iframe.className = 'redbot-iframe';
//     iframe.width = opts.width;
//     iframe.height = opts.height;
//     iframe.setAttribute('allow', 'clipboard-write;'); // extend as needed
//     iframe.style.background = '#fff';
//     return iframe;
//   }

//   function createLauncher(opts, position, onClick) {
//     var btn = document.createElement('button');
//     btn.className = 'redbot-launcher' + (position === 'bottom-left' ? ' left' : '');
//     btn.textContent = opts.launcherText || 'Chat';
//     btn.addEventListener('click', onClick);
//     return btn;
//   }

//   // Core loader
//   function RedbotLoad(publicKeyOrOptions, maybeOptions) {
//     var publicKey = typeof publicKeyOrOptions === 'string'
//       ? publicKeyOrOptions
//       : (publicKeyOrOptions && publicKeyOrOptions.publicKey);
//     var opts = normalizeOptions(typeof publicKeyOrOptions === 'string' ? maybeOptions : publicKeyOrOptions);

//     if (!publicKey) {
//       // Try to find from a placeholder
//       var placeholder = document.getElementById(opts.containerId);
//       if (placeholder && placeholder.dataset && placeholder.dataset.publicKey) {
//         publicKey = placeholder.dataset.publicKey;
//       }
//     }
//     if (!publicKey) {
//       console.warn('[Redbot] Missing public key.');
//       return null;
//     }

//     createStyles();

//     var parentOrigin = computeParentOrigin(opts.originOverride);
//     var widgetUrl = buildWidgetUrl(opts.host, publicKey, parentOrigin);

//     // Where to append
//     var placeholderEl = document.getElementById(opts.containerId);
//     var wrapper = createWrapper(opts);
//     var iframe = createIframe(widgetUrl, opts);

//     // Append iframe either inline (inside placeholder) or as floating
//     if (opts.position === 'inline' && placeholderEl) {
//       // Inline embed inside container
//       iframe.style.borderRadius = '8px';
//       iframe.style.boxShadow = 'none';
//       placeholderEl.innerHTML = '';
//       placeholderEl.appendChild(iframe);
//     } else {
//       wrapper.appendChild(iframe);
//       document.body.appendChild(wrapper);
//     }

//     // Optional launcher (for floating modes only)
//     var launcher = null;
//     if (opts.showLauncher && opts.position !== 'inline') {
//       launcher = createLauncher(opts, opts.position, function () {
//         var visible = wrapper.style.display !== 'none';
//         wrapper.style.display = visible ? 'none' : 'block';
//       });
//       document.body.appendChild(launcher);
//     }

//     // Public controller
//     var controller = {
//       publicKey: publicKey,
//       open: function () {
//         if (opts.position === 'inline') return; // always visible inline
//         wrapper.style.display = 'block';
//       },
//       close: function () {
//         if (opts.position === 'inline') return;
//         wrapper.style.display = 'none';
//       },
//       toggle: function () {
//         if (opts.position === 'inline') return;
//         wrapper.style.display = (wrapper.style.display === 'none') ? 'block' : 'none';
//       },
//       setPosition: function (pos) {
//         opts.position = pos;
//         if (launcher) {
//           if (pos === 'bottom-left') launcher.classList.add('left');
//           else launcher.classList.remove('left');
//         }
//         if (pos === 'bottom-left') wrapper.classList.add('left');
//         else wrapper.classList.remove('left');
//       },
//       setSize: function (w, h) {
//         if (w) iframe.width = String(w);
//         if (h) iframe.height = String(h);
//       },
//       destroy: function () {
//         if (launcher && launcher.parentNode) launcher.parentNode.removeChild(launcher);
//         if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
//       }
//     };

//     // Store reference
//     window.Redbot = window.Redbot || { widgets: {} };
//     window.Redbot.widgets[publicKey] = controller;

//     return controller;
//   }

//   // Expose global function
//   window.RedbotLoad = RedbotLoad;

//   // Auto-init on DOMContentLoaded: look for #redbot-chat[data-public-key]
//   document.addEventListener('DOMContentLoaded', function () {
//     var el = document.getElementById('redbot-chat');
//     if (!el) return;
//     var pk = el.getAttribute('data-public-key');
//     if (!pk) return;
//     // Allow overrides via data-*
//     var opts = {
//       publicKey: pk,
//       host: el.getAttribute('data-host') || undefined,
//       position: el.getAttribute('data-position') || undefined,
//       width: el.getAttribute('data-width') || undefined,
//       height: el.getAttribute('data-height') || undefined,
//       zIndex: el.getAttribute('data-z-index') || undefined,
//       open: (el.getAttribute('data-open') || 'true') !== 'false',
//       showLauncher: (el.getAttribute('data-launcher') || 'false') === 'true',
//       originOverride: el.getAttribute('data-origin-override') || undefined,
//       containerId: el.id || 'redbot-chat'
//     };
//     RedbotLoad(opts);
//   });
// })();


// function computeParentOrigin(originOverride) {
// // Always prefer explicit override (needed for file://)
// if (originOverride && typeof originOverride === 'string' && originOverride.trim() !== '') {
// return originOverride;
// }
// var o = (window.location && window.location.origin) || '';
// // Treat file:// or null-like as no origin and fall back to a dev default
// if (!o || o === 'null' || o === 'file://' || o.indexOf('file:') === 0) {
// return 'http://127.0.0.1:8000'; // or 'http://localhost:5500' if you serve your test page there
// }
// return o;
// }


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



(function () {
  'use strict';

  // Determine which host to load the iframe from (the host serving this script)
  function getScriptOrigin() {
    var s = document.currentScript ||
            document.querySelector('script[src*="/static/embed/bot.js"]') ||
            document.querySelector('script[src*="bot.js"]');
    if (!s) return window.location.origin;
    try {
      // Resolve relative src against the current page URL
      return new URL(s.getAttribute('src'), window.location.href).origin;
    } catch (e) {
      return window.location.origin;
    }
  }

  var SERVER_ORIGIN = getScriptOrigin() || window.location.origin || 'http://127.0.0.1:8000';

  function computeParentOrigin(originOverride) {
    // Always prefer explicit override (important for file:// pages)
    if (originOverride && typeof originOverride === 'string' && originOverride.trim() !== '') {
      return originOverride;
    }
    var o = (window.location && window.location.origin) || '';
    // Treat file:// as no origin and fall back to the server origin
    if (!o || o === 'null' || o === 'file://' || (typeof o === 'string' && o.indexOf('file:') === 0)) {
      return SERVER_ORIGIN;
    }
    return o;
  }

  function normalizeOptions(opts) {
    opts = opts || {};
    return {
      host: opts.host || SERVER_ORIGIN,
      originOverride: opts.originOverride || null,
      position: opts.position || 'bottom-right', // 'bottom-right' | 'bottom-left' | 'inline'
      width: String(opts.width || 360),
      height: String(opts.height || 520),
      zIndex: String(opts.zIndex || 999999),
      open: opts.open !== false,
      showLauncher: opts.showLauncher === true,
      launcherText: opts.launcherText || 'Chat',
      containerId: opts.containerId || 'redbot-chat'
    };
  }

  function createStyles() {
    if (document.getElementById('redbot-embed-styles')) return;
    var css = `
      .redbot-wrapper { position: fixed; bottom: 20px; right: 20px; }
      .redbot-wrapper.left { left: 20px; right: auto; }
      .redbot-iframe { border: none; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); background: #fff; }
      .redbot-launcher {
        position: fixed; bottom: 20px; right: 20px;
        background: #2563eb; color: #fff; border: none; border-radius: 9999px;
        padding: 12px 16px; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,0.15);
        font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; font-size: 14px;
      }
      .redbot-launcher.left { left: 20px; right: auto; }
    `;
    var el = document.createElement('style');
    el.id = 'redbot-embed-styles';
    el.textContent = css;
    document.head.appendChild(el);
  }

  function buildWidgetUrl(host, publicKey, parentOrigin) {
    var t = Date.now(); // cache buster
    return host.replace(/\/+$/, '') + '/embed/widget/' + encodeURIComponent(publicKey) +
           '?origin=' + encodeURIComponent(parentOrigin) + '&v=' + t;
  }

  function createWrapper(opts) {
    var wrapper = document.createElement('div');
    wrapper.className = 'redbot-wrapper' + (opts.position === 'bottom-left' ? ' left' : '');
    wrapper.style.zIndex = opts.zIndex;
    wrapper.style.display = opts.open ? 'block' : 'none';
    return wrapper;
  }

  function createIframe(url, opts) {
    var iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.className = 'redbot-iframe';
    iframe.width = opts.width;
    iframe.height = opts.height;
    iframe.setAttribute('allow', 'clipboard-write;'); // extend as needed
    iframe.title = 'Redbot Chat';
    return iframe;
  }

  function createLauncher(opts, position, onClick) {
    var btn = document.createElement('button');
    btn.className = 'redbot-launcher' + (position === 'bottom-left' ? ' left' : '');
    btn.textContent = opts.launcherText || 'Chat';
    btn.addEventListener('click', onClick);
    return btn;
  }

  function RedbotLoad(publicKeyOrOptions, maybeOptions) {
    var publicKey = typeof publicKeyOrOptions === 'string'
      ? publicKeyOrOptions
      : (publicKeyOrOptions && publicKeyOrOptions.publicKey);

    var opts = normalizeOptions(typeof publicKeyOrOptions === 'string' ? maybeOptions : publicKeyOrOptions);

    if (!publicKey) {
      // Try placeholder data attribute
      var placeholder = document.getElementById(opts.containerId);
      if (placeholder && placeholder.dataset && placeholder.dataset.publicKey) {
        publicKey = placeholder.dataset.publicKey;
      }
    }
    if (!publicKey) {
      console.warn('[Redbot] Missing public key.');
      return null;
    }

    createStyles();

    var parentOrigin = computeParentOrigin(opts.originOverride);
    var widgetUrl = buildWidgetUrl(opts.host, publicKey, parentOrigin);

    // Append iframe
    var placeholderEl = document.getElementById(opts.containerId);
    var wrapper = createWrapper(opts);
    var iframe = createIframe(widgetUrl, opts);

    if (opts.position === 'inline' && placeholderEl) {
      iframe.style.borderRadius = '8px';
      iframe.style.boxShadow = 'none';
      placeholderEl.innerHTML = '';
      placeholderEl.appendChild(iframe);
    } else {
      wrapper.appendChild(iframe);
      document.body.appendChild(wrapper);
    }

    // Optional launcher
    var launcher = null;
    if (opts.showLauncher && opts.position !== 'inline') {
      launcher = createLauncher(opts, opts.position, function () {
        var visible = wrapper.style.display !== 'none';
        wrapper.style.display = visible ? 'none' : 'block';
      });
      document.body.appendChild(launcher);
    }

    // Public controller
    var controller = {
      publicKey: publicKey,
      open: function () { if (opts.position !== 'inline') wrapper.style.display = 'block'; },
      close: function () { if (opts.position !== 'inline') wrapper.style.display = 'none'; },
      toggle: function () { if (opts.position !== 'inline') wrapper.style.display = (wrapper.style.display === 'none') ? 'block' : 'none'; },
      setPosition: function (pos) {
        opts.position = pos;
        if (launcher) {
          if (pos === 'bottom-left') launcher.classList.add('left');
          else launcher.classList.remove('left');
        }
        if (pos === 'bottom-left') wrapper.classList.add('left');
        else wrapper.classList.remove('left');
      },
      setSize: function (w, h) { if (w) iframe.width = String(w); if (h) iframe.height = String(h); },
      destroy: function () {
        if (launcher && launcher.parentNode) launcher.parentNode.removeChild(launcher);
        if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
      }
    };

    // Store reference
    window.Redbot = window.Redbot || { widgets: {} };
    window.Redbot.widgets[publicKey] = controller;

    return controller;
  }

  // Expose global
  window.RedbotLoad = RedbotLoad;

  // Auto-init from a placeholder with data-public-key
  document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('redbot-chat');
    if (!el) return;
    var pk = el.getAttribute('data-public-key');
    if (!pk) return;
    var opts = {
      publicKey: pk,
      position: el.getAttribute('data-position') || undefined,
      width: el.getAttribute('data-width') || undefined,
      height: el.getAttribute('data-height') || undefined,
      zIndex: el.getAttribute('data-z-index') || undefined,
      open: (el.getAttribute('data-open') || 'true') !== 'false',
      showLauncher: (el.getAttribute('data-launcher') || 'false') === 'true',
      originOverride: el.getAttribute('data-origin-override') || undefined,
      containerId: el.id || 'redbot-chat'
    };
    RedbotLoad(opts);
  });
})();


