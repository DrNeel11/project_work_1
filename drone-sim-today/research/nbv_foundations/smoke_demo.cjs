// Functional smoke check of the generated script with a minimal DOM adapter.
// This checks bindings and every precomputed state, not browser layout/rendering.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('demo/index.html', 'utf8');
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
const elements = new Map(ids.map(id=>[id, {innerHTML:'', textContent:'', className:'', disabled:false, checked:false,
  handlers:{}, addEventListener(type, fn) {this.handlers[type]=fn;}}]));
const context = vm.createContext({document:{getElementById(id) {
  assert(elements.has(id), `Missing element: ${id}`); return elements.get(id);
}},setInterval:()=>1,clearInterval:()=>{}});
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInContext(script, context);
let renders=0;
for (let scenario=0;scenario<6;scenario++) {
  elements.get('scenario').handlers.change({target:{value:String(scenario)}});
  for(let stage=0;stage<8;stage++) {
    vm.runInContext(`setStage(${stage})`,context);
    assert(elements.get('stage-title').textContent.startsWith(`${stage}.`));
    assert(!elements.get('metrics').innerHTML.includes('NaN'));
    for(let step=0;step<3;step++) {
      elements.get('step').handlers.click();
      assert(elements.get('scene').innerHTML.includes('HOME'));
      assert(!elements.get('scene').innerHTML.includes('undefined'));
      renders++;
    }
    elements.get('back').handlers.click();
    elements.get('reveal').checked=true;
    elements.get('reveal').handlers.change();
    assert(elements.get('world').textContent.includes('Sampled latent state'));
  }
}
console.log(`UI smoke passed: ${renders} replay renders across 6 scenarios × 8 stages. Browser layout not tested.`);
