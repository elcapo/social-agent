import{i as v}from"./icons.CavvgR0t.js";import{b as s,e as t}from"./dom.1PcoZyDp.js";const i="http://localhost:8000/api";async function g(){const[n,d,u,r,b]=await Promise.all([fetch(`${i}/sources`).then(e=>e.json()),fetch(`${i}/seeds`).then(e=>e.json()),fetch(`${i}/ideas`).then(e=>e.json()),fetch(`${i}/drafts`).then(e=>e.json()),fetch(`${i}/drafts/scheduled`).then(e=>e.json()).catch(()=>[])]),h=r.filter(e=>e.status==="published"),f=r.filter(e=>e.status==="draft");s("stat-sources").textContent=String(n.length),s("stat-seeds").textContent=String(d.length),s("stat-ideas").textContent=String(u.length),s("stat-drafts").textContent=String(f.length),s("stat-published").textContent=String(h.length);const o=d.slice(-5).reverse();s("recent-seeds").innerHTML=o.length?`<div class="flex flex-col gap-3">${o.map(e=>`
            <a href="/seeds/edit?id=${e.id}" class="flex items-center justify-between gap-3 py-3 px-1 no-underline hover:bg-base-200 -mx-1 px-3 rounded-lg transition-colors duration-150" title="Abrir semilla: ${t(e.title)}">
              <div class="min-w-0">
                <div class="font-semibold text-sm truncate">${t(e.title)}</div>
                <div class="text-xs text-base-content/60">${e.created_at?new Date(e.created_at).toLocaleDateString():""}</div>
              </div>
              <span class="badge badge-sm badge-soft ${e.status==="pending"?"badge-warning":e.status==="used"?"badge-success":e.status==="approved"?"badge-info":"badge-error"}">${t(e.status)}</span>
            </a>`).join("")}</div>`:'<div class="alert bg-base-200 text-sm">Aún no hay semillas.</div>';const c=r.slice(-5).reverse();s("recent-drafts").innerHTML=c.length?`<div class="flex flex-col gap-3">${c.map(e=>{const a=e.content?e.content.substring(0,80)+(e.content.length>80?"…":""):"(vacío)";return`
            <a href="/drafts/edit?id=${e.id}" class="flex items-center justify-between gap-3 py-3 px-1 no-underline hover:bg-base-200 -mx-1 px-3 rounded-lg transition-colors duration-150" title="Abrir borrador: ${t(a)}">
              <div class="min-w-0">
                <div class="font-semibold text-sm truncate">${t(a)}</div>
                <div class="text-xs text-base-content/60">${e.created_at?new Date(e.created_at).toLocaleDateString():""}</div>
              </div>
              <span class="badge badge-sm badge-soft ${e.status==="draft"?"badge-warning":e.status==="approved"?"badge-info":e.status==="published"?"badge-success":"badge-error"}">${t(e.status)}</span>
            </a>`}).join("")}</div>`:'<div class="alert bg-base-200 text-sm">Aún no hay borradores.</div>';const l=b.slice().sort((e,a)=>new Date(e.scheduled_at||0).getTime()-new Date(a.scheduled_at||0).getTime());s("scheduled-drafts").innerHTML=l.length?`<div class="divide-y divide-base-200">${l.map(e=>{const a=e.content?e.content.substring(0,60)+(e.content.length>60?"…":""):"(vacío)",p=new Date(e.scheduled_at||0)<=new Date;return`
            <a href="/drafts/edit?id=${e.id}" class="flex items-center justify-between gap-3 py-3 px-1 no-underline hover:bg-base-200 -mx-1 px-3 rounded-lg transition-colors duration-150" title="${t(a)}">
              <div class="min-w-0">
                <div class="font-semibold text-sm truncate">${t(a)}</div>
                <div class="text-xs text-base-content/60 capitalize">${t(e.platform)}</div>
              </div>
              <span class="badge badge-sm badge-soft ${p?"badge-warning":"badge-secondary"} whitespace-nowrap" title="${t(e.scheduled_at)}">${new Date(e.scheduled_at||0).toLocaleString()}</span>
            </a>`}).join("")}</div>`:'<div class="alert bg-base-200 text-sm">No hay borradores programados.</div>'}s("btn-run-scheduler").addEventListener("click",async()=>{const n=s("btn-run-scheduler");n.disabled=!0,n.textContent="Ejecutando…";try{if(!(await fetch(`${i}/scheduler/run`,{method:"POST"})).ok)throw new Error("Scheduler failed");await g()}catch{}finally{n.disabled=!1,n.innerHTML=`${v("play",14)} Ejecutar planificador`}});g();
