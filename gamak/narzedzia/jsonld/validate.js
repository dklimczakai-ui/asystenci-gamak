const fs = require('fs');
const path = require('path');

function findHtml(dir, acc = []) {
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    const st = fs.statSync(p);
    if (st.isDirectory()) findHtml(p, acc);
    else if (f.endsWith('.html') && !f.startsWith('._')) acc.push(p);
  }
  return acc;
}

const roots = process.argv.slice(2);
const files = roots.flatMap(r => findHtml(r));
const re = /<script[^>]+application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi;

let errors = 0;
for (const f of files) {
  const html = fs.readFileSync(f, 'utf8');
  let m, i = 0;
  while ((m = re.exec(html)) !== null) {
    i++;
    try {
      JSON.parse(m[1].trim());
    } catch (e) {
      errors++;
      console.log(`\n❌ ${f} [block ${i}]`);
      console.log(`   ${e.message}`);
      const lines = m[1].split('\n');
      const errMatch = e.message.match(/position (\d+)/);
      if (errMatch) {
        const pos = parseInt(errMatch[1]);
        let cur = 0, ln = 0;
        for (; ln < lines.length; ln++) {
          if (cur + lines[ln].length + 1 > pos) break;
          cur += lines[ln].length + 1;
        }
        console.log(`   line ~${ln+1}: ${(lines[ln]||'').trim().slice(0,120)}`);
      }
    }
  }
}
console.log(`\n${errors} errors in ${files.length} files.`);
