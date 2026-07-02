/* Kiwi Dialectic community layer — Kōrero
   - Loads Giscus (GitHub Discussions, MIT) into #kd-comments
   - Uses `pathname` mapping so every page has its own Discussion thread
   - Privacy-first: no third-party trackers; commenters use GitHub accounts
   - Graceful fallback if Giscus fails to load
*/
(function () {
  var REPO         = "robertmccallnz/ai-literacy-for-families";
  var REPO_ID      = "R_kgDOTHnLZQ";
  var CATEGORY     = "General";
  var CATEGORY_ID  = "DIC_kwDOTHnLZc4DAWmJ";
  var DISCUSSIONS_URL = "https://github.com/" + REPO + "/discussions";
  var PRIVACY_URL  = "/ai-literacy-for-families/privacy/";
  var GISCUS_SRC   = "https://giscus.app/client.js";

  function markBroken(root) {
    if (root) root.classList.add("is-broken");
  }

  function rewriteHead(root) {
    var lede = root.querySelector('.kc-lede');
    if (lede) {
      lede.innerHTML =
        'Kōrero mai — join the discussion below. Comments are hosted on ' +
        '<a href="' + DISCUSSIONS_URL + '" target="_blank" rel="noopener">GitHub Discussions</a> ' +
        'via <a href="https://giscus.app" target="_blank" rel="noopener">Giscus</a>. ' +
        'Free, open-source, no tracking. You\u2019ll need a free GitHub account to post.';
    }
    var meta = root.querySelector('.kc-meta');
    if (meta) {
      meta.innerHTML =
        'One thread per page, threaded replies, reactions, markdown supported. ' +
        'Everything you post is public and lives in the repo. ' +
        'See <a href="' + PRIVACY_URL + '">the privacy note</a> for the full kōrero.';
    }
    var fb = root.querySelector('.kc-fallback');
    if (fb) {
      fb.innerHTML =
        'Widget not loading? Jump straight into the ' +
        '<a href="' + DISCUSSIONS_URL + '" target="_blank" rel="noopener">GitHub Discussion for this page</a>, ' +
        'or reply on <a href="https://kiwidialectic.substack.com" target="_blank" rel="noopener">Substack</a> or ' +
        '<a href="https://facebook.com/kiwidialectic" target="_blank" rel="noopener">Facebook</a>.';
    }
    var live = root.querySelector('.kc-live');
    if (live) {
      var label = live.querySelector('span:last-child');
      if (label) label.textContent = 'Kōrero open';
    }
  }

  function loadGiscus(mount) {
    return new Promise(function (resolve, reject) {
      while (mount.firstChild) mount.removeChild(mount.firstChild);
      var s = document.createElement('script');
      s.src = GISCUS_SRC;
      s.async = true;
      s.crossOrigin = 'anonymous';
      s.setAttribute('data-repo', REPO);
      s.setAttribute('data-repo-id', REPO_ID);
      s.setAttribute('data-category', CATEGORY);
      s.setAttribute('data-category-id', CATEGORY_ID);
      s.setAttribute('data-mapping', 'pathname');
      s.setAttribute('data-strict', '1');
      s.setAttribute('data-reactions-enabled', '1');
      s.setAttribute('data-emit-metadata', '0');
      s.setAttribute('data-input-position', 'bottom');
      s.setAttribute('data-theme', 'dark_dimmed');
      s.setAttribute('data-lang', 'en');
      s.setAttribute('data-loading', 'lazy');
      s.onload = resolve;
      s.onerror = reject;
      mount.appendChild(s);
    });
  }

  function boot() {
    var root = document.querySelector('.kd-community');
    if (!root) return;
    var mount = root.querySelector('#kd-comments');
    if (!mount) return;

    rewriteHead(root);
    mount.innerHTML = '<div class="kc-loading">Loading kōrero\u2026</div>';

    loadGiscus(mount).catch(function () {
      markBroken(root);
      var loader = mount.querySelector('.kc-loading');
      if (loader) loader.parentNode.removeChild(loader);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
