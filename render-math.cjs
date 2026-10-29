const katex = require('./vendor/katex.cjs');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const result = JSON.parse(input).map(({tex, display}) => katex.renderToString(tex, {
    displayMode: display, output: 'mathml', throwOnError: false, strict: 'ignore', trust: false
  }));
  process.stdout.write(JSON.stringify(result));
});
