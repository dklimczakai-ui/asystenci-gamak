const WebSocket = require('ws');
const ws = new WebSocket(require('fs').readFileSync('/tmp/ws-url.txt', 'utf-8').trim());

let id = 0;
const calls = new Map();
const send = (method, params={}) => new Promise(res => {
  const myId = ++id;
  calls.set(myId, res);
  ws.send(JSON.stringify({id: myId, method, params}));
});

ws.on('message', m => {
  const msg = JSON.parse(m);
  if (msg.id && calls.has(msg.id)) { calls.get(msg.id)(msg); calls.delete(msg.id); }
  if (msg.method === 'Runtime.consoleAPICalled') {
    const args = (msg.params.args || []).map(a => a.value || a.description || '?').join(' ');
    console.log('[browser]', msg.params.type, args);
  }
  if (msg.method === 'Runtime.exceptionThrown') {
    console.log('[EXCEPTION]', JSON.stringify(msg.params.exceptionDetails).substring(0, 400));
  }
});

ws.on('open', async () => {
  await send('Runtime.enable');
  await send('Page.enable');
  console.log('Connected. Waiting 8s for full init...');
  await new Promise(r => setTimeout(r, 8000));
  
  // Force re-eval / get state
  const queries = [
    ['ready', 'document.querySelector("[x-data]")._x_dataStack[0].ready'],
    ['view', 'document.querySelector("[x-data]")._x_dataStack[0].view'],
    ['loadingMsg', 'document.querySelector("[x-data]")._x_dataStack[0].loadingMsg'],
    ['contacts.length', 'document.querySelector("[x-data]")._x_dataStack[0].contacts.length'],
    ['pipelines.length', 'document.querySelector("[x-data]")._x_dataStack[0].pipelines.length'],
    ['indexedDB version', 'new Promise(r => { const x = indexedDB.open("gamak-crm"); x.onsuccess = e => { r(x.result.version); x.result.close(); }; x.onerror = () => r("ERR"); })'],
  ];
  for (const [label, expr] of queries) {
    try {
      const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true});
      console.log(`  ${label} =`, r.result?.result?.value, r.result?.exceptionDetails ? '(ERR)' : '');
    } catch (e) { console.log('  err:', label); }
  }

  // Check if any clicks work — try clicking Settings button
  console.log('\n--- Click on "Kontakty" tab ---');
  const click = await send('Runtime.evaluate', {expression: `
    const btn = [...document.querySelectorAll('header nav button')].find(b => b.textContent.includes('Kontakty'));
    btn ? (btn.click(), document.querySelector("[x-data]")._x_dataStack[0].view) : 'BUTTON NOT FOUND';
  `, returnByValue: true});
  console.log('  After click view =', click.result?.result?.value);
  
  process.exit(0);
});

ws.on('error', e => console.error('WS error:', e.message));
setTimeout(() => { console.log('TIMEOUT'); process.exit(1); }, 25000);
