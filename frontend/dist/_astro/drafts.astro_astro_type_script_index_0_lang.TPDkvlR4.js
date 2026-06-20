import{i as c}from"./icons.CavvgR0t.js";import{b as r,g as h,e as b,q as u,a as C}from"./dom.1PcoZyDp.js";const l="http://localhost:8000/api",d=r("error-msg"),S=["draft","approved","rejected","published","failed"],q={draft:"warning",approved:"info",rejected:"error",published:"success",failed:"error"},A={draft:"borrador",approved:"aprobado",rejected:"rechazado",published:"publicado",failed:"fallido"},x=t=>A[t]||t,_=["twitter","linkedin"],i={statuses:[],platforms:[],q:""},f=new Set,M=new URLSearchParams(window.location.search),v=M.get("status");v&&S.includes(v)&&(i.statuses=[v],f.add("status"));function m(t){d.textContent=t,d.classList.remove("alert-info"),d.classList.add("alert-error"),d.classList.remove("hidden")}function $(t){d.textContent=t,d.classList.remove("alert-error"),d.classList.add("alert-info"),d.classList.remove("hidden")}function g(){d.classList.add("hidden")}function k(t){return new Promise(e=>{const a=r("confirm-dialog");r("confirm-msg").textContent=t,a.showModal(),setTimeout(()=>r("confirm-yes").focus(),0),r("confirm-yes").onclick=()=>{a.close(),e(!0)},r("confirm-no").onclick=()=>{a.close(),e(!1)}})}function H(t){return new Promise(e=>{const a=r("prompt-dialog");r("prompt-msg").textContent=t;const s=r("prompt-input");s.value="",a.showModal(),setTimeout(()=>s.focus(),0),r("prompt-ok").onclick=()=>{a.close(),e(s.value)},r("prompt-cancel").onclick=()=>{a.close(),e(null)}})}function y(t){return`<span class="badge badge-sm badge-soft ${{draft:"badge-warning",approved:"badge-info",rejected:"badge-error",published:"badge-success",failed:"badge-error"}[t.status]||"badge-ghost"}" title="Estado ${x(t.status)}">${x(t.status)}</span>`}function E(t){const e=t.media_urls||[],a=t.media_paths||[],s=[...e.map(o=>({src:o})),...a.map(o=>({src:`${l}/media/${o.split("/").pop()}`}))];return s.length?`<div class="flex gap-1">${s.slice(0,3).map(o=>`<img src="${b(o.src)}" class="w-8 h-8 object-cover rounded" alt="Vista previa del medio" loading="lazy" />`).join("")}${s.length>3?`<span class="text-xs text-base-content/60 self-center">+${s.length-3}</span>`:""}</div>`:'<span class="text-base-content/30">—</span>'}function L(t){return t.scheduled_at?`<span class="badge badge-sm badge-soft badge-secondary whitespace-nowrap" title="${b(t.scheduled_at)}">${c("calendar",12,"inline-block")} ${new Date(t.scheduled_at).toLocaleString()}</span>`:'<span class="text-base-content/30">—</span>'}function T(t){const e=[`<a href="/drafts/edit?id=${t.id}" class="btn btn-square btn-ghost btn-sm" aria-label="Editar borrador" title="Editar borrador">${c("edit",16)}</a>`];return t.status==="draft"&&(e.push(`<button class="btn btn-square btn-ghost btn-sm text-success" data-action="approve" data-id="${t.id}" aria-label="Aprobar borrador" title="Aprobar borrador">${c("check",16)}</button>`),e.push(`<button class="btn btn-square btn-ghost btn-sm text-error" data-action="reject" data-id="${t.id}" aria-label="Rechazar borrador" title="Rechazar (pedir motivo)">${c("circle-x",16)}</button>`)),t.status==="approved"&&e.push(`<button class="btn btn-square btn-ghost btn-sm text-primary" data-action="publish" data-id="${t.id}" aria-label="Publicar borrador" title="Publicar borrador">${c("send",16)}</button>`),t.scheduled_at&&e.push(`<button class="btn btn-square btn-ghost btn-sm" data-action="unschedule" data-id="${t.id}" aria-label="Cancelar programación" title="Cancelar programación">${c("calendar-x",16)}</button>`),e.join("")}async function p(){g();const t=new URLSearchParams;i.statuses.forEach(n=>t.append("statuses",n)),i.platforms.forEach(n=>t.append("platforms",n)),i.q&&t.set("q",i.q);const e=t.toString(),s=await(await fetch(`${l}/drafts${e?"?"+e:""}`)).json(),o=r("drafts-list");if(!s.length){o.innerHTML='<div class="alert bg-base-200 text-sm">Aún no hay borradores. Pulsa "Generar desde idea" para crear algunos.</div>';return}const j=s.map(n=>`
          <tr>
            <td><span class="badge badge-sm badge-ghost capitalize">${b(n.platform)}</span></td>
            <td><div class="text-sm text-base-content/70 max-w-xs truncate" title="${b(n.content||"")}">${n.content?b(n.content.substring(0,100))+(n.content.length>100?"…":""):"—"}</div></td>
            <td>${E(n)}</td>
            <td>${y(n)}</td>
            <td>${L(n)}</td>
            <td class="text-sm text-base-content/60">${n.created_at?new Date(n.created_at).toLocaleDateString():"—"}</td>
            <td><div class="flex gap-1">${T(n)}</div></td>
          </tr>`).join(""),P=s.map(n=>`
          <div class="card bg-base-100 border border-base-300 shadow-sm">
            <div class="card-body p-4 gap-2">
              <div class="flex items-center justify-between gap-2">
                <span class="badge badge-sm badge-ghost capitalize">${b(n.platform)}</span>
                ${y(n)}
              </div>
              <p class="text-sm text-base-content/80 line-clamp-3">${n.content?b(n.content.substring(0,200))+(n.content.length>200?"…":""):"—"}</p>
              ${E(n)}
              <div class="flex items-center justify-between gap-2 text-xs text-base-content/60 flex-wrap">
                <span>${L(n)}</span>
                <span>${n.created_at?new Date(n.created_at).toLocaleDateString():"—"}</span>
              </div>
              <div class="flex gap-1 pt-1 border-t border-base-200">${T(n)}</div>
            </div>
          </div>`).join("");o.innerHTML=`
        <div class="hidden md:block overflow-x-auto">
          <table class="table table-zinc">
            <thead>
              <tr>
                <th>Plataforma</th>
                <th>Contenido</th>
                <th>Multimedia</th>
                <th>Estado</th>
                <th>Programado</th>
                <th>Creado</th>
                <th><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>${j}</tbody>
          </table>
        </div>
        <div class="md:hidden flex flex-col gap-3">${P}</div>`}r("drafts-list").addEventListener("click",async t=>{const e=t.target.closest("[data-action]");if(!e)return;g();const a=e.dataset.id??"";try{switch(e.dataset.action){case"approve":{const s=await fetch(`${l}/drafts/${a}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:"approved"})});if(!s.ok)throw new Error(await h(s));break}case"reject":{const s=await H("Motivo del rechazo (opcional):");if(s===null)return;const o=await fetch(`${l}/drafts/${a}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:"rejected",notes:s})});if(!o.ok)throw new Error(await h(o));break}case"publish":{if(!await k("¿Publicar este borrador?"))return;const o=await fetch(`${l}/publish/${a}`,{method:"POST"});if(!o.ok)throw new Error(await h(o));break}case"unschedule":{if(!await k("¿Cancelar la programación de este borrador?"))return;const o=await fetch(`${l}/drafts/${a}/unschedule`,{method:"POST"});if(!o.ok)throw new Error(await h(o));break}}p()}catch(s){m("Error: "+s.message)}});r("btn-run-scheduler").addEventListener("click",async()=>{g();const t=r("btn-run-scheduler");t.disabled=!0,t.textContent="Ejecutando…";try{const e=await fetch(`${l}/scheduler/run`,{method:"POST"});if(!e.ok)throw new Error(await h(e));const a=await e.json();a.published===0&&a.failed===0?$("No hay borradores listos para publicar."):$(`Planificador: ${a.published} publicados, ${a.failed} fallidos.`),p()}catch(e){m("Error: "+e.message)}finally{t.disabled=!1,t.innerHTML=`${c("play",14)} Ejecutar planificador`}});r("btn-generate").addEventListener("click",async()=>{g();const t=r("generate-modal"),e=r("idea-select"),s=await(await fetch(`${l}/ideas?status=pending`)).json();e.innerHTML=s.length?s.map(o=>`<option value="${o.id}">${b(o.title)}</option>`).join(""):'<option value="">No hay ideas pendientes</option>',t.showModal(),setTimeout(()=>e.focus(),0)});r("modal-cancel").addEventListener("click",()=>{r("generate-modal").close()});r("modal-generate").addEventListener("click",async()=>{const t=r("idea-select").value;if(!t){m("Selecciona una idea.");return}const e=u("#generate-modal input[type=checkbox]:checked").map(s=>s.value);if(!e.length){m("Selecciona al menos una plataforma.");return}const a=r("modal-generate");a.disabled=!0,a.textContent="Generando…",g();try{const s=await fetch(`${l}/drafts/generate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({idea_id:t,platforms:e})});if(!s.ok)throw new Error(await h(s));r("generate-modal").close(),p()}catch(s){m("Error: "+s.message)}finally{a.disabled=!1,a.textContent="Generar"}});function w(){const t=r("active-filters");if(t.innerHTML="",f.has("status")){const e=new Set(i.statuses),a=S.map(s=>`
          <label class="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" class="checkbox checkbox-xs" data-status="${s}" ${e.has(s)?"checked":""} />
            <span class="badge badge-sm badge-soft badge-${q[s]}">${x(s)}</span>
          </label>`).join("");t.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Estado</span>
            <div class="flex items-center gap-1.5 flex-wrap">${a}</div>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="status" aria-label="Quitar filtro de estado" title="Quitar filtro de estado">${c("close",14)}</button>
          </div>`}if(f.has("platform")){const e=new Set(i.platforms),a=_.map(s=>`
          <label class="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" class="checkbox checkbox-xs" data-platform="${s}" ${e.has(s)?"checked":""} />
            <span class="badge badge-sm badge-soft capitalize">${s}</span>
          </label>`).join("");t.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Plataforma</span>
            <div class="flex items-center gap-1.5 flex-wrap">${a}</div>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="platform" aria-label="Quitar filtro de plataforma" title="Quitar filtro de plataforma">${c("close",14)}</button>
          </div>`}f.has("keyword")&&(t.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Palabra clave</span>
            <input type="text" class="input input-xs w-40" id="filter-q" placeholder="buscar contenido" value="${C(i.q)}" />
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="keyword" aria-label="Quitar filtro de palabra clave" title="Quitar filtro de palabra clave">${c("close",14)}</button>
          </div>`),z(),O()}function z(){u("[data-add-filter]").forEach(t=>{const e=t.dataset.addFilter??"",a=t.closest("li");a&&(f.has(e)?a.classList.add("hidden"):a.classList.remove("hidden"))})}function O(){u("[data-remove-filter]").forEach(e=>{e.addEventListener("click",()=>{const a=e.dataset.removeFilter??"";f.delete(a),a==="status"&&(i.statuses=[]),a==="platform"&&(i.platforms=[]),a==="keyword"&&(i.q=""),w(),p()})}),u("[data-status]").forEach(e=>{e.addEventListener("change",()=>{i.statuses=u("[data-status]:checked").map(a=>a.dataset.status??"").filter(Boolean),p()})}),u("[data-platform]").forEach(e=>{e.addEventListener("change",()=>{i.platforms=u("[data-platform]:checked").map(a=>a.dataset.platform??"").filter(Boolean),p()})});const t=r("filter-q");t&&t.addEventListener("input",()=>{i.q=t.value,clearTimeout(t._t),t._t=setTimeout(p,300)})}u("[data-add-filter]").forEach(t=>{t.addEventListener("click",()=>{const e=t.dataset.addFilter??"";if(f.has(e))return;f.add(e);const a=t.closest("details");a&&(a.open=!1),w(),p()})});w();p();
