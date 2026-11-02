// Expand "See more" in rendered feed posts (a local UI toggle, no network side effect).
(() => {
  let n = 0;
  for (const art of document.querySelectorAll('[aria-posinset]')) {
    for (const b of art.querySelectorAll('[role=button]')) {
      if (/^(See more|Zobacz więcej)$/.test(b.innerText.trim())) { try { b.click(); n++; } catch (e) {} }
    }
  }
  return n;
})()
