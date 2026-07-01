
const acorn = require('acorn');
const fs = require('fs');
const code = fs.readFileSync('script0.js', 'utf8');
try {
    acorn.parse(code, {ecmaVersion: 2020});
    console.log('No syntax error found by Acorn!');
} catch (e) {
    console.log(e.message);
    const lines = code.split('\n');
    const lineIndex = e.loc.line - 1;
    console.log('Line ' + e.loc.line + ': ' + lines[lineIndex]);
    console.log(' '.repeat(e.loc.column) + '^');
}
