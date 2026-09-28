// Functional control smoke check, not a browser layout test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'demo/index.html'),'utf8');
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
const elements=new Map(ids.map(id=>[id,{innerHTML:'',textContent:'',value:'',checked:false,disabled:false,handlers:{},addEventListener(name,fn){this.handlers[name]=fn;}}]));
const context=vm.createContext({document:{getElementById(id){assert(elements.has(id),id);return elements.get(id);}}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
let renders=0;
for(let s=0;s<3;s++)for(let p=0;p<5;p++)for(const day of [1,18,24,48]){
 elements.get('scenario').handlers.change({target:{value:s}});
 elements.get('policy').handlers.change({target:{value:p}});
 elements.get('day').handlers.input({target:{value:day}});
 for(let r=0;r<4;r++){
  elements.get('region').handlers.change({target:{value:r}});
  assert(!elements.get('regions').innerHTML.includes('NaN'));
  assert(elements.get('plot').innerHTML.includes('<path'));
  assert(!elements.get('plot').innerHTML.includes('undefined'));
  renders++;
 }
}
console.log(`Stability UI: ${renders} region/scenario/policy/day renders passed. Browser layout not tested.`);
