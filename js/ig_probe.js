// Probe: describe rendered Instagram feed articles (read-only).
(() => {
  const arts = [...document.querySelectorAll('article')];
  return JSON.stringify({
    url: location.href,
    n: arts.length,
    sample: arts.slice(0, 4).map(a => ({
      text: a.innerText.slice(0, 400),
      links: [...a.querySelectorAll('a[href]')].slice(0, 12).map(x => [x.getAttribute('href'), x.innerText.trim().slice(0, 30)]),
      times: [...a.querySelectorAll('time')].map(t => [t.getAttribute('datetime'), t.innerText]),
      verified: !!a.querySelector('svg[aria-label="Verified"]'),
      imgs: [...a.querySelectorAll('img')].map(i => [i.alt.slice(0, 60), i.naturalWidth]).slice(0, 5),
      video: !!a.querySelector('video'),
    })),
  });
})()
