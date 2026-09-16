// Classic, dependency-free capture runs before deferred renderer modules.
(() => {
  let mount = null;
  let currentCall = null;
  const unavailable = 'برای مشاهده پیشنهاد، پیوند خصوصی ارسال‌شده را باز کنید.';
  const capture = () => {
    const capability = window.location.hash.slice(1);
    window.history.replaceState(null, '', window.location.pathname);
    currentCall = null;
    let quoteId = '';
    try {
      if (!capability || capability.length > 4096 || !/^[A-Za-z0-9_.-]+$/.test(capability)) throw new Error('unavailable');
      const parts = capability.split('.');
      if (parts.length !== 3) throw new Error('unavailable');
      const claims = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      if (typeof claims.quote !== 'string' || !/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(claims.quote)) throw new Error('unavailable');
      quoteId = claims.quote;
    } catch {
      if (mount) mount(null);
      else document.getElementById('root').textContent = unavailable;
      return;
    }
    currentCall = async (body, key) => {
      const response = await fetch(`/api/quote-capability/quotes/${quoteId}`, {
        method: body ? 'POST' : 'GET', credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
        headers: { Authorization: `QuoteCapability ${capability}`, ...(body ? { 'Content-Type': 'application/json', 'Idempotency-Key': key } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) throw new Error(response.status === 409 ? 'changed' : 'unavailable');
      return response.json();
    };
    if (mount) mount(currentCall);
  };
  document.addEventListener('quote-customer-ready', event => {
    mount = event.detail;
    if (currentCall) mount(currentCall);
  }, { once: true });
  // Opening another private link in this same document is a fragment
  // navigation, not a new script load. Clear it and discard the old view.
  window.addEventListener('hashchange', capture);
  capture();
})();
