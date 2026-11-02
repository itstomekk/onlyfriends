// Runs on facebook.com/<me>/friends_all. Returns rendered friend cards.
// __SELF__ is replaced by collect_fb.py with your own profile key.
(() => {
  const norm = (href) => {
    try {
      const u = new URL(href);
      const parts = u.pathname.split('/').filter(Boolean);
      if (parts[0] === 'profile.php') return u.searchParams.get('id') ? 'id:' + u.searchParams.get('id') : null;
      return parts.length === 1 ? parts[0].toLowerCase() : null;
    } catch (e) { return null; }
  };
  const seen = {};
  for (const a of document.querySelectorAll('[role=main] a[href]')) {
    const t = a.innerText.trim();
    if (!t || /mutual friend|followers|following|^Friends$/i.test(t)) continue;
    if (/sk=friends_mutual|\/friends_mutual/.test(a.href)) continue;
    const k = norm(a.href);
    if (!k || ['__SELF__', 'friends'].includes(k)) continue;
    if (!seen[k]) seen[k] = t;
  }
  return JSON.stringify(seen);
})()
