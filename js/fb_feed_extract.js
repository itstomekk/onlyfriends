// Runs inside the Facebook page. Returns JSON of currently rendered feed posts.
// Expands "See more" inside rendered posts first (read-only UI toggle).
(() => {
  const norm = (href) => {
    try {
      const u = new URL(href, location.origin);
      if (!/facebook\.com$/.test(u.hostname)) return null;
      const parts = u.pathname.split('/').filter(Boolean);
      if (!parts.length) return null;
      if (parts[0] === 'profile.php') return u.searchParams.get('id') ? 'id:' + u.searchParams.get('id') : null;
      if (parts[0] === 'people' && parts[2]) return 'id:' + parts[2];
      if (['groups', 'stories', 'photo', 'watch', 'reel', 'events', 'hashtag', 'share', 'pages', 'marketplace'].includes(parts[0])) return null;
      return parts[0].toLowerCase();
    } catch (e) { return null; }
  };
  const clean = (href) => { try { const u = new URL(href); u.searchParams.delete('__cft__[0]'); u.searchParams.delete('__tn__'); return u.toString().replace(/\?$/, ''); } catch (e) { return href; } };
  const out = [];
  for (const art of document.querySelectorAll('[aria-posinset]')) {
    if (!art.innerText.trim()) continue;
    const head = art.querySelector('h2, h3, h4');
    const headLinks = head ? [...head.querySelectorAll('a[href]')] : [];
    const authorA = headLinks.find(a => norm(a.href)) || null;
    // group posts: "Name ▸ Group" - author is a person link inside the header
    const groupA = headLinks.find(a => /\/groups\//.test(a.href)) || null;
    const permA = [...art.querySelectorAll('a[href]')].find(a => /\/(posts|permalink|videos|reel)\/|story_fbid=|\/photo\/\?fbid=|\/groups\/[^/]+\/(posts|permalink)\//.test(a.href) && a.innerText.trim().length > 0 && a.innerText.trim().length < 40);
    const msgNodes = art.querySelectorAll('[data-ad-preview=message], [data-ad-comet-preview=message]');
    let text = [...msgNodes].map(n => n.innerText.trim()).join('\n\n');
    const imgs = [...art.querySelectorAll('img')]
      .filter(i => /scontent|fbcdn/.test(i.src) && (i.naturalWidth || i.width) >= 120)
      .map(i => ({ src: i.src, alt: i.alt || '' }))
      .filter(i => !/profile picture/i.test(i.alt))
      .slice(0, 6);
    const hasVideo = !!art.querySelector('video');
    out.push({
      author: authorA ? authorA.innerText.trim() : (head ? head.innerText.trim() : ''),
      author_key: authorA ? norm(authorA.href) : null,
      author_url: authorA ? clean(authorA.href) : null,
      header: head ? head.innerText.trim().slice(0, 200) : '',
      group: groupA ? groupA.innerText.trim() : null,
      permalink: permA ? clean(permA.href) : null,
      time_text: permA ? permA.innerText.trim() : null,
      text: text.slice(0, 5000),
      images: imgs,
      has_video: hasVideo,
      raw_text: art.innerText.slice(0, 4000),
    });
  }
  return JSON.stringify(out);
})()
