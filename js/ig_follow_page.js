// Read-only: one page of a follow list via the endpoint Instagram's own web app uses.
// Placeholders replaced by collect_ig_friends.py: __PATH__ (relative API path).
(async () => {
  const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const r = await fetch('https://www.instagram.com' + '__PATH__', {
    headers: { 'X-IG-App-ID': '936619743392459', 'X-Requested-With': 'XMLHttpRequest',
               'X-CSRFToken': csrf, 'Accept': '*/*' },
    credentials: 'include' });
  const t = await r.text();
  let j = null;
  try { j = JSON.parse(t); } catch (e) { return JSON.stringify({ status: r.status, error: 'not json' }); }
  if (j.data && j.data.user) {
    const u = j.data.user;
    return JSON.stringify({ status: r.status, id: u.id, followers: u.edge_followed_by.count, following: u.edge_follow.count });
  }
  return JSON.stringify({
    status: r.status,
    users: (j.users || []).map(u => ({ username: u.username, full_name: u.full_name || '', verified: !!u.is_verified })),
    next_max_id: j.next_max_id || null,
  });
})()
