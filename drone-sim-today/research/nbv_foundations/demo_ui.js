"use strict";
const $ = id => document.getElementById(id);
let selectedScenario = 0, selectedStage = 0, frameIndex = 0, timer = null;
const num = (x, places = 3) => Number(x).toFixed(places);
const percent = x => `${num(100*x, 1)}%`;
const table = (headers, rows) => `<thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(c=>`<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>`;
const colors = ["#8ac7e0", "#efbb80", "#c2ed83"];
const xy = i => { const v = i < 0 ? {x:DATA.base[0], y:DATA.base[1]} : DATA.views[i]; return [300+v.x*62, 156-v.y*62]; };
function scene(result, frame) {
  const parts = [`<rect x="263" y="118" width="74" height="76" rx="8" fill="#293a30" stroke="#5a705d"/><text x="300" y="151" text-anchor="middle" fill="#ebf1e7" font-size="11">ASSET</text><text x="300" y="169" text-anchor="middle" fill="#a8b9aa" font-size="9">1 component</text>`];
  for (const edge of frame.plan.edges) {
    const [x1,y1]=xy(edge.i), [x2,y2]=xy(edge.j);
    parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#6d8656" stroke-width="2" stroke-dasharray="5 5" opacity=".6"/>`);
  }
  let last = -1;
  for (let f=0; f<frameIndex; f++) {
    const next=result.replay.frames[f].next;
    if(next < 0) break;
    const [x1,y1]=xy(last), [x2,y2]=xy(next);
    parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#c2ed83" stroke-width="3"/>`);
    last=next;
  }
  const target = frame.next < 0 ? -1 : frame.next;
  const [x1,y1]=xy(frame.position), [x2,y2]=xy(target);
  parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#ebf1e7" stroke-width="2" stroke-dasharray="4 4"/>`);
  DATA.views.forEach((v,i)=>{
    const [x,y]=xy(i), possible=frame.feasible.includes(i), chosen=i===frame.next;
    parts.push(`<g opacity="${possible || i===frame.position ? 1 : .3}"><circle cx="${x}" cy="${y}" r="${chosen?13:8}" fill="${colors[i%3]}" ${chosen?'stroke="#ebf1e7" stroke-width="2"':""}/><text x="${x}" y="${y-17}" fill="#ebf1e7" font-size="10" text-anchor="middle">${i}</text>${possible?"":`<text x="${x}" y="${y+4}" text-anchor="middle" fill="#101715" font-size="15">×</text>`}</g>`);
  });
  const [bx,by]=xy(-1);
  parts.push(`<rect x="${bx-7}" y="${by-7}" width="14" height="14" fill="#ebf1e7"/><text x="${bx}" y="${by+28}" text-anchor="middle" fill="#a8b9aa" font-size="10">HOME</text>`);
  const [px,py]=xy(frame.position);
  parts.push(`<circle cx="${px}" cy="${py}" r="18" fill="none" stroke="#ebf1e7" stroke-width="1"/><text x="16" y="304" fill="#a8b9aa" font-size="11">Remaining travel resource: ${num(frame.energy,2)} · acquisition limit: 2</text>`);
  $("scene").innerHTML=parts.join("");
}
function render() {
  const scenario=DATA.scenarios[selectedScenario], result=scenario.results[selectedStage], stage=result.stage;
  const frame=result.replay.frames[Math.min(frameIndex,result.replay.frames.length-1)];
  $("scenario-description").textContent=scenario.description;
  $("stages").innerHTML=DATA.stages.map((s,i)=>`<button class="stage ${i<selectedStage?'done':''}" data-stage="${i}" aria-current="${i===selectedStage}"><span>${String(i).padStart(2,"0")} / ${i===7?'CANDIDATE':'FOUNDATION'}</span>${s.name}</button>`).join("");
  $("stage-title").textContent=`${selectedStage}. ${stage.name} · + ${stage.added}`;
  $("status").textContent=stage.status;
  $("status").className=`badge ${selectedStage===7?'candidate':''}`;
  $("explanation").textContent=stage.explanation;
  $("flow").innerHTML=DATA.stages.map((s,i)=>`<span class="${i<=selectedStage?'active':''}">${s.name}</span>`).join("");
  $("announcement").textContent=selectedStage===7?`K=${DATA.top_k} proposed pairs; all feasible singleton policies and stopping retained. Compare cost and total runtime with stage 6.`:selectedStage===0?"Start with geometric coverage. Add dimensions to see whether the choice, belief or cost changes.":`Only the capability named above changes from the previous stage. Current-episode Bayesian updates, candidate poses and resource limits are shared.`;
  $("previous").disabled=selectedStage===0; $("next").disabled=selectedStage===7;
  $("back").disabled=frameIndex===0; $("step").disabled=frame.next<0;
  $("step-label").textContent=`Replay ${frameIndex} / ${result.replay.frames.length-1}`;
  const last=frameIndex?result.replay.frames[frameIndex-1]:null;
  $("observation").textContent=(last?`Observed ${['low','middle','high'][last.observation]} at ${DATA.views[last.next].name}. `:"")+(frame.next<0?`Stop acquisition → ${frame.decision}; return home.`:`Next: ${DATA.views[frame.next].name}. Maintenance action if stopping now: ${frame.decision}.`);
  $("world").textContent=$("reveal").checked?`Sampled latent state: damage=${result.replay.state[0]}, fast rate=${result.replay.state[1]}, artifact=${result.replay.state[2]}. This one replay does not determine the expected-cost chart.`:"World state hidden. All stages share the same latent-state and per-view noise draws.";
  scene(result,frame);
  $("memory-mode").textContent=stage.memory==='none'?'No cross-mission memory':stage.memory;
  $("belief-bars").innerHTML=[['Damage now',frame.belief.damage],['Fast deterioration',frame.belief.fast],['Artifact positive',frame.belief.artifact],['Failure by service',frame.belief.failure]].map(([name,p])=>`<div class="barrow"><span>${name}</span><div class="bar"><b style="width:${100*p}%"></b></div><span>${percent(p)}</span></div>`).join("");
  $("covariance").textContent=`Cov(D,N) = ${num(frame.belief.covariance)}`;
  $("joint").innerHTML=frame.belief.joint.map((p,i)=>`<div class="cell" style="background:rgba(194,237,131,${.05+.7*p});color:${p>.6?'#101715':'#ebf1e7'}">${percent(p)}<small>D${DATA.states[i][0]} R${DATA.states[i][1]} N${DATA.states[i][2]}</small></div>`).join("");
  $("history").innerHTML=scenario.history.length?scenario.history.map(([t,v,y])=>`<span>t=${t} · ${DATA.views[v].name}<br>${['low','middle','high'][y]}</span>`).join(""):'<span>No previous acquisitions</span>';
  $("memory-note").textContent=`Current time: ${scenario.now}. ${stage.memory==='none'?'History is shown for comparison but not supplied to this planner.':stage.memory==='snapshot'?'Historical observations are treated as contemporaneous. Temporal transitions are omitted.':stage.memory==='temporal'?'Damage/rate and artifact marginals are stored separately; cross-dependence is discarded at historical updates.':'Timestamped joint belief preserves dependencies through the history.'} Current-episode updates always retain joint evidence.`;
  $("metrics").innerHTML=[[num(result.metrics.cost),'Expected total cost'],[num(result.metrics.views,2),'Expected acquisitions'],[percent(result.metrics.missed),'Unrepaired failure probability']].map(([value,label])=>`<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");
  const maxCost=Math.max(...scenario.results.map(r=>r.metrics.cost));
  $("costs").innerHTML=scenario.results.map((r,i)=>`<div class="result-row ${i===selectedStage?'selected':''}"><span>${i}. ${r.stage.name}</span><div class="result-bar"><b style="width:${100*r.metrics.cost/maxCost}%"></b></div><span>${num(r.metrics.cost)}</span></div>`).join("");
  const delta=selectedStage?result.metrics.cost-scenario.results[selectedStage-1].metrics.cost:0;
  $("delta").textContent=selectedStage?Math.abs(delta)<1e-8?'No cost change in this scenario. An added capability is not automatically useful.':`Change from previous stage: ${delta>0?'+':''}${num(delta)} cost units (${delta<0?'improvement':'worse'}).`:'All eight stages are visible so unfavorable results remain inspectable.';
  const get=(m,p)=>scenario.factorial.find(r=>r.memory===m&&r.policy===p).cost;
  $("factorial").innerHTML=table(['Memory','Myopic','Exact two-view','Sparse graph'],['none','snapshot','temporal','joint'].map(m=>[m,...['myopic','exact','graph'].map(p=>num(get(m,p)))]));
  const interaction=(get('joint','myopic')-get('joint','exact'))-(get('temporal','myopic')-get('temporal','exact'));
  $("interaction").textContent=`Interaction contrast: ${num(interaction)}. Positive means lookahead helps more with joint than factorized temporal memory in this conditional scenario; this is not a statistical significance test.`;
  $("score-label").textContent=stage.policy==='coverage'?'New schematic patches per acquisition cost; maximize.':stage.policy==='entropy'?'Expected damage information per acquisition cost; maximize.':'Predicted acquisition + travel + terminal maintenance cost; minimize. Stop is a competing action.';
  $("scores").innerHTML=table(['View','Score'],frame.plan.scores.map(s=>[DATA.views[s.i].name,num(s.score)]));
  const exactCost=scenario.results[6].metrics.cost;
  $("sweep").innerHTML=table(['K pairs','Total cost','Δ from exact','Regret bound','Exact expansions'],scenario.sweep.map(r=>[r.k,num(r.cost),num(r.cost-exactCost),r.certificate?num(r.certificate.max_regret):'0',r.branch_expansions]));
  const certificate=scenario.results[7].first.certificate;
  $("certificate").textContent=certificate?`Model-based certificate: optimal two-view cost lies in [${num(certificate.lower_bound)}, ${num(certificate.upper_bound)}]. Sparse-policy regret is at most ${num(certificate.max_regret)} cost units. The bound uses optimistic perfect-information relaxations for omitted branches; it does not require the exhaustive solution. It need not be tight and does not cover model misspecification.`:'No feasible acquisition; stop is optimal under the model.';
  $("scaling").innerHTML=table(['Views','Policy','Expansions / proxies / bounds','Median ms'],DATA.scaling.map(r=>[r.candidates,r.policy,`${r.branch_expansions} / ${r.proxy_pairs} / ${r.bound_checks}`,num(r.median_ms,2)]));
  $("provenance").textContent=JSON.stringify(DATA.provenance,null,2);
  if(DATA.benchmark) {
    $("benchmark-note").textContent=`${DATA.benchmark.episodes} generated histories, seed ${DATA.benchmark.seed}. Same histories and constraints for every stage. The matched group uses correct model assumptions; drift changes artifact persistence without informing the planner. Lower cost is better.`;
    $("benchmark").innerHTML=table(['Stage','Matched-model mean cost','Artifact-drift mean cost'],DATA.stages.map((s,i)=>[s.name,num(DATA.benchmark.summaries.matched_model.mean_costs[i]),num(DATA.benchmark.summaries.artifact_drift.mean_costs[i])]));
  } else {
    $("benchmark-note").textContent='No compatible sampled-history results embedded. Run benchmark_demo.py with the same top-k, then build_demo.py to include them.';
    $("benchmark").innerHTML='';
  }
}
function setStage(i) { selectedStage=Math.max(0,Math.min(7,i));frameIndex=0;render(); }
function stopTour() { if(timer!==null) clearInterval(timer);timer=null;$("tour").textContent='Play stages'; }
$("scenario").innerHTML=DATA.scenarios.map((s,i)=>`<option value="${i}">${s.name}</option>`).join("");
$("scenario").addEventListener('change',e=>{stopTour();selectedScenario=Number(e.target.value);frameIndex=0;render();});
$("stages").addEventListener('click',e=>{const button=e.target.closest('[data-stage]');if(button){stopTour();setStage(Number(button.dataset.stage));}});
$("previous").addEventListener('click',()=>{stopTour();setStage(selectedStage-1);});
$("next").addEventListener('click',()=>{stopTour();setStage(selectedStage+1);});
$("step").addEventListener('click',()=>{frameIndex=Math.min(frameIndex+1,DATA.scenarios[selectedScenario].results[selectedStage].replay.frames.length-1);render();});
$("back").addEventListener('click',()=>{frameIndex=Math.max(0,frameIndex-1);render();});
$("reveal").addEventListener('change',render);
$("tour").addEventListener('click',()=>{if(timer!==null){stopTour();return;}if(selectedStage===7)setStage(0);$("tour").textContent='Pause stages';timer=setInterval(()=>{if(selectedStage===7){stopTour();return;}setStage(selectedStage+1);},3500);});
render();
