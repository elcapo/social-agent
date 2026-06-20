const v="http://localhost:8000/api",y=document.getElementById("error-msg");function u(e){y.textContent=e,y.classList.remove("hidden")}function p(){y.classList.add("hidden")}async function E(e){try{const t=await e.json();return Array.isArray(t.detail)?t.detail[0]?.msg||"Request failed":t.detail||"Request failed"}catch{return"Request failed"}}function k(e){try{return new URL(e).hostname}catch{return e}}async function o(){p();const e=new URLSearchParams;(r.types||[]).forEach(n=>e.append("source_types",n)),r.q&&e.set("q",r.q),r.enabled!==null&&e.set("enabled",String(r.enabled));const t=e.toString(),s=await(await fetch(`${v}/sources${t?"?"+t:""}`)).json(),c=document.getElementById("sources-list");if(!s.length){c.innerHTML='<div class="alert bg-base-200 text-sm">No sources configured. Add one to get started.</div>';return}c.innerHTML=`<ul class="list bg-base-100 border border-base-300 rounded-box divide-y divide-base-200">
        ${s.map(n=>`
          <li class="list-row flex-col items-stretch gap-2 py-3">
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="font-medium">${l(n.name)}</span>
                <span class="badge badge-sm badge-soft shrink-0">${l(n.source_type)}</span>
                ${n.enabled===!1?'<span class="badge badge-sm badge-soft badge-error shrink-0">disabled</span>':""}
              </div>
              <span class="badge badge-sm badge-ghost shrink-0">${n.priority}</span>
              <div class="flex gap-1 shrink-0">
                <a href="/sources/edit?id=${n.id}" class="btn btn-square btn-ghost btn-sm" aria-label="Edit source">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                </a>
                <button class="btn btn-square btn-ghost btn-sm text-error" data-action="delete" data-id="${n.id}" aria-label="Delete source">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
            <div class="flex items-center gap-3 text-sm text-base-content/50">
              <div class="flex items-center gap-1 min-w-0 flex-1">
                <a href="${l(n.url)}" target="_blank" rel="noopener noreferrer" class="truncate hover:text-primary transition-colors" title="${l(n.url)}">${l(k(n.url))}</a>
                <button class="btn btn-square btn-ghost btn-xs shrink-0" data-action="copy" data-url="${l(n.url)}" aria-label="Copy URL">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
              </div>
              <div class="flex flex-wrap gap-1">
                ${(n.tags||[]).map(m=>`<span class="badge badge-sm badge-soft badge-primary">${l(m)}</span>`).join("")}
              </div>
            </div>
            <div class="text-xs text-base-content/40">${n.created_at?new Date(n.created_at).toLocaleDateString():"—"}</div>
          </li>`).join("")}
      </ul>`}function l(e){if(!e)return"";const t=document.createElement("div");return t.appendChild(document.createTextNode(e)),t.innerHTML}function w(){document.getElementById("form-title").textContent="Add Source",document.getElementById("modal-save").textContent="Save",document.getElementById("src-name").value="",document.getElementById("src-type").value="rss",document.getElementById("src-url").value="",document.getElementById("src-priority").value="2",document.getElementById("src-tags").value="",document.getElementById("src-config").value="",document.getElementById("src-config").placeholder='{"full_content": true}',document.getElementById("form-modal").showModal()}document.getElementById("src-type").addEventListener("change",()=>{const e=document.getElementById("src-type").value,t=e==="rss"?'{"full_content": true}':e==="link_scraper"?'{"url_pattern": "/blog/.+", "max_items": 10}':'{"key": "value"}';document.getElementById("src-config").placeholder=t});document.getElementById("sources-list").addEventListener("click",async e=>{const t=e.target.closest("[data-action]");if(t){if(p(),t.dataset.action==="delete"){const a=t.dataset.id;if(!(await fetch(`${v}/sources/${a}`,{method:"DELETE"})).ok){u("Failed to delete source");return}o()}else if(t.dataset.action==="copy")try{await navigator.clipboard.writeText(t.dataset.url);const a=t.querySelector("svg"),s=t.innerHTML;t.innerHTML='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',t.classList.add("text-success"),setTimeout(()=>{t.innerHTML=s,t.classList.remove("text-success")},1500)}catch{u("Failed to copy URL")}}});document.getElementById("btn-add").addEventListener("click",()=>{p(),w()});document.getElementById("modal-cancel").addEventListener("click",()=>{document.getElementById("form-modal").close()});document.getElementById("modal-save").addEventListener("click",async()=>{const e=document.getElementById("src-name").value.trim(),t=document.getElementById("src-type").value,a=document.getElementById("src-url").value.trim(),s=parseInt(document.getElementById("src-priority").value),c=document.getElementById("src-tags").value.trim();if(!e||!a){u("Name and URL are required.");return}const n=document.getElementById("modal-save");n.disabled=!0;const m=n.textContent;n.textContent="Saving...",p();try{const g=c?c.split(",").map(i=>i.trim()):[],b=new URLSearchParams({name:e,source_type:t,url:a,priority:String(s)});g.forEach(i=>b.append("tags",i));const f=document.getElementById("src-config").value.trim();if(f)try{JSON.parse(f),b.append("config",f)}catch{u("Config is not valid JSON."),n.disabled=!1,n.textContent=m;return}const h=await fetch(`${v}/sources?${b}`,{method:"POST"});if(!h.ok)throw new Error(await E(h));document.getElementById("form-modal").close(),["src-name","src-url","src-tags"].forEach(i=>document.getElementById(i).value=""),o()}catch(g){u("Error: "+g.message)}finally{n.disabled=!1,n.textContent=m}});const L=["rss","webpage","link_scraper","social","manual"],r={types:[],q:"",enabled:null},d=new Set;function B(e){return l(e).replace(/"/g,"&quot;")}function x(){const e=document.getElementById("active-filters");if(e.innerHTML="",d.has("type")){const t=new Set(r.types),a=L.map(s=>`
          <label class="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" class="checkbox checkbox-xs" data-type="${s}" ${t.has(s)?"checked":""} />
            <span class="badge badge-sm badge-soft">${s}</span>
          </label>`).join("");e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Type</span>
            <div class="flex items-center gap-1.5 flex-wrap">${a}</div>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="type" aria-label="Remove type filter">✕</button>
          </div>`}if(d.has("keyword")&&(e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Keyword</span>
            <input type="text" class="input input-xs w-40" id="filter-q" placeholder="search name, url, tags" value="${B(r.q)}" />
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="keyword" aria-label="Remove keyword filter">✕</button>
          </div>`),d.has("enabled")){const t=r.enabled===null?"all":r.enabled?"enabled":"disabled";e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Enabled</span>
            <select class="select select-xs" id="filter-enabled">
              <option value="all" ${t==="all"?"selected":""}>All</option>
              <option value="enabled" ${t==="enabled"?"selected":""}>Enabled</option>
              <option value="disabled" ${t==="disabled"?"selected":""}>Disabled</option>
            </select>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="enabled" aria-label="Remove enabled filter">✕</button>
          </div>`}I(),$()}function I(){document.querySelectorAll("[data-add-filter]").forEach(e=>{const t=e.dataset.addFilter,a=e.closest("li");d.has(t)?a.classList.add("hidden"):a.classList.remove("hidden")})}function $(){document.querySelectorAll("[data-remove-filter]").forEach(a=>{a.addEventListener("click",()=>{const s=a.dataset.removeFilter;d.delete(s),s==="type"&&(r.types=[]),s==="keyword"&&(r.q=""),s==="enabled"&&(r.enabled=null),x(),o()})}),document.querySelectorAll("[data-type]").forEach(a=>{a.addEventListener("change",()=>{r.types=Array.from(document.querySelectorAll("[data-type]:checked")).map(s=>s.dataset.type),o()})});const e=document.getElementById("filter-q");e&&e.addEventListener("input",()=>{r.q=e.value,clearTimeout(e._t),e._t=setTimeout(o,300)});const t=document.getElementById("filter-enabled");t&&t.addEventListener("change",()=>{const a=t.value;r.enabled=a==="all"?null:a==="enabled",o()})}document.querySelectorAll("[data-add-filter]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.addFilter;if(d.has(t))return;d.add(t);const a=e.closest("details");a&&(a.open=!1),x(),o()})});o();
