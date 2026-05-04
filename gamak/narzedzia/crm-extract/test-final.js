const WebSocket = require('ws');
const ws = new WebSocket(require('fs').readFileSync('/tmp/ws-url.txt', 'utf-8').trim());
let id = 0; const calls = new Map();
const send = (m, p={}) => new Promise(res => { const i=++id; calls.set(i,res); ws.send(JSON.stringify({id:i,method:m,params:p})); });

ws.on('message', m => {
  const x = JSON.parse(m);
  if (x.id && calls.has(x.id)) { calls.get(x.id)(x); calls.delete(x.id); }
  if (x.method === 'Runtime.consoleAPICalled') {
    const a = (x.params.args||[]).map(v => v.value || v.description || '?').join(' ');
    if (a.includes('[CRM]')) console.log(' ', a);
  }
});

ws.on('open', async () => {
  await send('Runtime.enable');
  // Force reload to clean state
  await send('Page.reload', {ignoreCache: true});
  await new Promise(r => setTimeout(r, 6000));
  
  // Get state
  const queries = [
    ['ready', 'document.querySelector("[x-data]")._x_dataStack[0].ready'],
    ['contacts.length', 'document.querySelector("[x-data]")._x_dataStack[0].contacts.length'],
    ['Wieslaw company', 'document.querySelector("[x-data]")._x_dataStack[0].contacts.find(c => c.email === "wklimczak.sportmanager@gmail.com")?.company'],
  ];
  for (const [k, e] of queries) {
    const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: true});
    console.log(' ', k, '=', r.result?.result?.value);
  }
  process.exit(0);
});
setTimeout(() => process.exit(0), 20000);
