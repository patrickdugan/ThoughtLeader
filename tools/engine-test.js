const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync('../frame-theater.html', 'utf8');
let js = html.split('<script>')[1].split('</scr' + 'ipt>')[0];
js += `
globalThis.__p = () => ({att: state.att, asc: state.asc, flags: state.flags.slice(),
                         nodeId, traceLen: state.trace.length, nodeDefined: !!node, advancing});
globalThis.__take = take; globalThis.__goto = goto; globalThis.__loop = loop;
globalThis.__reset = reset; globalThis.__STORY = STORY; globalThis.__eligible = eligible;
globalThis.__choices = () => el.choices._buttons.slice();
`;

const timers = [];
const ctx2d = new Proxy({}, { get: (t, k) => {
  if (k === 'createImageData') return (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
  if (k === 'createRadialGradient') return () => ({ addColorStop() {} });
  return () => {};
}, set: () => true });

function mkEl(tag) {
  const e = { tag, children: [], _on: {}, dataset: {}, style: {}, _buttons: [] };
  let _html = '';
  Object.defineProperty(e, 'innerHTML', {
    get: () => _html,
    set: v => { _html = v; if (v === '') { e.children = []; e._buttons = []; } }
  });
  e.appendChild = c => { e.children.push(c); collectButtons(e, c); };
  e.addEventListener = (t, fn) => (e._on[t] = e._on[t] || []).push(fn);
  e.getContext = () => ctx2d;
  e.remove = () => {};
  e.click = () => (e._on.click || []).forEach(f => f());
  return e;
}
function collectButtons(root, c) {
  if (c.tag === 'button') root._buttons.push(c);
  (c.children || []).forEach(x => collectButtons(root, x));
}

const ids = {};
['scene','portrait','speaker','line','choices','slug-scene','att-v','att-f','asc-v','asc-f','flags','log','host','restart','export']
  .forEach(i => ids[i] = mkEl('div'));

const sandbox = {
  console,
  Math, Date, JSON, Uint8ClampedArray, parseInt, Blob: function(){}, URL: { createObjectURL: () => '', revokeObjectURL: () => {} },
  document: { getElementById: i => ids[i], createElement: mkEl, addEventListener: () => {} },
  window: { matchMedia: () => ({ matches: true }) },
  requestAnimationFrame: () => {},
  setInterval: fn => { timers.push(fn); return timers.length; },
  clearInterval: () => {},
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js, sandbox);

const pump = () => { const t = timers.splice(0); t.forEach(f => f()); };
const P = () => sandbox.__p();
let fails = 0;
const ok = (name, cond, extra='') => { console.log((cond?'  PASS  ':'  FAIL  ') + name + (extra?'   '+extra:'')); if(!cond) fails++; };

// --- 1. double-click on a choice must apply once
sandbox.__reset(); pump();
ok('starts at brief', P().nodeId === 'brief');
const c0 = sandbox.__STORY.brief.choices[0];   // att:2, flag conflict-of-interest
sandbox.__take(c0);
sandbox.__take(c0);                            // the second click, before render
pump();
ok('double take applies att once', P().att === 2, 'att=' + P().att);
ok('double take logs one trace row', P().traceLen === 1, 'rows=' + P().traceLen);
ok('double take sets flag once', P().flags.filter(f => f === 'conflict-of-interest').length === 1);
ok('landed on audit', P().nodeId === 'audit', P().nodeId);

// --- 2. double-click on Continue must advance once
let btns = sandbox.__choices();
ok('audit renders one Continue', btns.length === 1);
btns[0].click(); btns[0].click();               // twice, fast
pump();
ok('double Continue advances once', P().nodeId === 'converge', P().nodeId);

// --- 3. terminal: goto(null) must not corrupt `node`
sandbox.__goto('ante_close', null); pump();
ok('at terminal', P().nodeId === 'ante_close');
ok('terminal renders no Continue', sandbox.__choices().length === 0);
sandbox.__goto(null, null);
ok('goto(null) leaves node defined', P().nodeDefined === true);
let threw = null; try { sandbox.__loop(); } catch (e) { threw = e.message; }
ok('render loop survives', threw === null, threw || '');

// --- 4. gating across acts
sandbox.__reset(); pump();
sandbox.__goto('ante_return', null); pump();
ok('without attested-identity: 2 options', sandbox.__choices().length === 2, sandbox.__choices().length + '');
sandbox.__reset(); pump();
sandbox.__take({ to: 'rack', flag: 'attested-identity' }); pump();
sandbox.__goto('ante_return', null); pump();
ok('with attested-identity: 3 options', sandbox.__choices().length === 3, sandbox.__choices().length + '');

console.log(fails ? `\n${fails} FAILED` : '\nall green');
process.exit(fails ? 1 : 0);
