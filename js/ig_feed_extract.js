// Runs inside Instagram (Following feed). Returns JSON of rendered posts.
// Expands "more" captions first (read-only UI toggle). Never likes/comments.
(() => {
  for (const b of document.querySelectorAll('article span[role=button], article div[role=button]')) {
    if (/^(more|więcej)$/i.test(b.innerText.trim())) { try { b.click(); } catch (e) {} }
  }
  const out = [];
  for (const a of document.querySelectorAll('article')) {
    const raw = a.innerText || '';
    if (!raw.trim()) continue;
    const userA = [...a.querySelectorAll('a[href]')].find(x => /^\/[A-Za-z0-9._]+\/$/.test(x.getAttribute('href')) && x.innerText.trim());
    const permA = [...a.querySelectorAll('a[href]')].find(x => /^\/(p|reel)\/[^/]+\/$/.test(x.getAttribute('href')));
    const t = a.querySelector('time[datetime]');
    const user = userA ? userA.getAttribute('href').replace(/\//g, '') : null;
    // caption: block that starts with the username after the action bar
    let caption = '';
    for (const s of a.querySelectorAll('h1, span[dir=auto], div[dir=auto]')) {
      const txt = s.innerText.trim();
      if (txt.length > caption.length && !/^\d/.test(txt) && txt !== user && !/profile picture|^Liked by|^View all \d+ comments/i.test(txt)) {
        if (s.closest('ul') || s.closest('header')) continue;
        caption = txt;
      }
    }
    if (user && caption.startsWith(user)) caption = caption.slice(user.length).trim();
    const imgs = [...a.querySelectorAll('img')]
      .filter(i => !/profile picture/i.test(i.alt) && (i.naturalWidth || i.width) >= 300)
      .map(i => ({ src: i.currentSrc || i.src, alt: i.alt || '' }))
      .slice(0, 4);
    const v = a.querySelector('video');
    if (!imgs.length && v && v.poster) imgs.push({ src: v.poster, alt: 'video' });
    out.push({
      user,
      verified: !!a.querySelector('svg[aria-label=Verified]'),
      sponsored: /(^|\n)(Sponsored|Sponsorowane|Paid partnership[^\n]*)(\n|$)/i.test(raw),
      suggested: /Suggested for you|Suggested posts|Proponowane/i.test(raw),
      permalink: permA ? 'https://www.instagram.com' + permA.getAttribute('href') : null,
      datetime: t ? t.getAttribute('datetime') : null,
      text: caption.replace(/\s*(… )?more$/, '').slice(0, 4000),
      images: imgs,
      has_video: !!v,
    });
  }
  return JSON.stringify(out);
})()
