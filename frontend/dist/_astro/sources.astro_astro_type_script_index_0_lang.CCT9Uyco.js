import{i as o}from"./icons.CavvgR0t.js";import{b as t,g as w,q as m,e as l,a as T}from"./dom.1PcoZyDp.js";const L="http://localhost:8000/api",x=t("error-msg"),E={rss:"rss",webpage:"globe",link_scraper:"link",social:"users",manual:"type"},_={1:"Alta",2:"Media",3:"Baja"};function v(e){x.textContent=e,x.classList.remove("hidden")}function h(){x.classList.add("hidden")}function S(e){try{return new URL(e).hostname}catch{return e}}async function c(){h();const e=new URLSearchParams;i.types.forEach(s=>e.append("source_types",s)),i.q&&e.set("q",i.q),i.enabled!==null&&e.set("enabled",String(i.enabled));const a=e.toString(),r=await(await fetch(`${L}/sources${a?"?"+a:""}`)).json(),p=t("sources-list");if(!r.length){p.innerHTML='<div class="alert bg-base-200 text-sm">No hay fuentes configuradas. Añade una para empezar.</div>';return}p.innerHTML=`<ul class="list bg-base-100 border border-base-300 rounded-box divide-y divide-base-200">
        ${r.map(s=>{const g=E[s.source_type]?o(E[s.source_type],12):"",u=_[String(s.priority)]||String(s.priority);return`
          <li class="list-row flex-col items-stretch gap-2 py-3">
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="font-medium truncate" title="${l(s.name)}">${l(s.name)}</span>
                <span class="badge badge-sm badge-soft shrink-0 gap-1" title="Tipo de fuente">${g}${l(s.source_type)}</span>
                ${s.enabled===!1?'<span class="badge badge-sm badge-soft badge-error shrink-0">desactivada</span>':""}
              </div>
              <span class="badge badge-sm badge-ghost shrink-0" title="Prioridad ${u}">${s.priority}</span>
              <div class="flex gap-1 shrink-0">
                <a href="/sources/edit?id=${s.id}" class="btn btn-square btn-ghost btn-sm" aria-label="Editar fuente" title="Editar fuente">${o("edit",16)}</a>
                <button class="btn btn-square btn-ghost btn-sm text-error" data-action="delete" data-id="${s.id}" aria-label="Eliminar fuente" title="Eliminar fuente">${o("trash",16)}</button>
              </div>
            </div>
            <div class="flex items-center gap-3 text-sm text-base-content/60">
              <div class="flex items-center gap-1 min-w-0 flex-1">
                <a href="${l(s.url)}" target="_blank" rel="noopener noreferrer" class="truncate hover:text-primary transition-colors" title="${l(s.url)}">${l(S(s.url))}</a>
                <button class="btn btn-square btn-ghost btn-xs shrink-0" data-action="copy" data-url="${l(s.url)}" aria-label="Copiar URL" title="Copiar URL">${o("copy",14)}</button>
              </div>
              <div class="flex flex-wrap gap-1">
                ${(s.tags||[]).map(b=>`<span class="badge badge-sm badge-soft badge-primary">${l(b)}</span>`).join("")}
              </div>
            </div>
            <div class="text-xs text-base-content/60">${s.created_at?new Date(s.created_at).toLocaleDateString():"—"}</div>
          </li>`}).join("")}
      </ul>`}function q(){t("form-title").textContent="Añadir fuente",t("modal-save").textContent="Guardar",t("src-name").value="",t("src-type").value="rss",t("src-url").value="",t("src-priority").value="2",t("src-tags").value="",t("src-config").value="",t("src-config").placeholder='{"full_content": true}',t("form-modal").showModal(),setTimeout(()=>t("src-name").focus(),0)}t("src-type").addEventListener("change",()=>{const e=t("src-type").value,a=e==="rss"?'{"full_content": true}':e==="link_scraper"?'{"url_pattern": "/blog/.+", "max_items": 10}':'{"key": "value"}';t("src-config").placeholder=a});t("sources-list").addEventListener("click",async e=>{const a=e.target.closest("[data-action]");if(a){if(h(),a.dataset.action==="delete"){const n=a.dataset.id??"";if(!(await fetch(`${L}/sources/${n}`,{method:"DELETE"})).ok){v("No se pudo eliminar la fuente");return}c()}else if(a.dataset.action==="copy")try{await navigator.clipboard.writeText(a.dataset.url??"");const n=a.innerHTML;a.innerHTML=o("check",14),a.classList.add("text-success"),setTimeout(()=>{a.innerHTML=n,a.classList.remove("text-success")},1500)}catch{v("No se pudo copiar la URL")}}});t("btn-add").addEventListener("click",()=>{h(),q()});t("modal-cancel").addEventListener("click",()=>{t("form-modal").close()});t("modal-save").addEventListener("click",async()=>{const e=t("src-name").value.trim(),a=t("src-type").value,n=t("src-url").value.trim(),r=parseInt(t("src-priority").value),p=t("src-tags").value.trim();if(!e||!n){v("El nombre y la URL son obligatorios.");return}const s=t("modal-save");s.disabled=!0;const g=s.textContent;s.textContent="Guardando…",h();try{const u=p?p.split(",").map(f=>f.trim()):[],b=new URLSearchParams({name:e,source_type:a,url:n,priority:String(r)});u.forEach(f=>b.append("tags",f));const y=t("src-config").value.trim();if(y)try{JSON.parse(y),b.append("config",y)}catch{v("La configuración no es JSON válido."),s.disabled=!1,s.textContent=g;return}const $=await fetch(`${L}/sources?${b}`,{method:"POST"});if(!$.ok)throw new Error(await w($));t("form-modal").close(),["src-name","src-url","src-tags"].forEach(f=>t(f).value=""),c()}catch(u){v("Error: "+u.message)}finally{s.disabled=!1,s.textContent=g}});const M=["rss","webpage","link_scraper","social","manual"],i={types:[],q:"",enabled:null},d=new Set;function k(){const e=t("active-filters");if(e.innerHTML="",d.has("type")){const a=new Set(i.types),n=M.map(r=>`
          <label class="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" class="checkbox checkbox-xs" data-type="${r}" ${a.has(r)?"checked":""} />
            <span class="badge badge-sm badge-soft">${r}</span>
          </label>`).join("");e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Tipo</span>
            <div class="flex items-center gap-1.5 flex-wrap">${n}</div>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="type" aria-label="Quitar filtro de tipo" title="Quitar filtro de tipo">${o("close",14)}</button>
          </div>`}if(d.has("keyword")&&(e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Palabra clave</span>
            <input type="text" class="input input-xs w-40" id="filter-q" placeholder="buscar nombre, url, etiquetas" value="${T(i.q)}" />
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="keyword" aria-label="Quitar filtro de palabra clave" title="Quitar filtro de palabra clave">${o("close",14)}</button>
          </div>`),d.has("enabled")){const a=i.enabled===null?"all":i.enabled?"enabled":"disabled";e.innerHTML+=`
          <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 rounded-full">
            <span class="text-xs font-medium text-base-content/60">Estado activo</span>
            <select class="select select-xs" id="filter-enabled">
              <option value="all" ${a==="all"?"selected":""}>Todas</option>
              <option value="enabled" ${a==="enabled"?"selected":""}>Activadas</option>
              <option value="disabled" ${a==="disabled"?"selected":""}>Desactivadas</option>
            </select>
            <button class="btn btn-ghost btn-xs btn-circle" data-remove-filter="enabled" aria-label="Quitar filtro de estado activo" title="Quitar filtro de estado activo">${o("close",14)}</button>
          </div>`}A(),C()}function A(){m("[data-add-filter]").forEach(e=>{const a=e.dataset.addFilter??"",n=e.closest("li");n&&(d.has(a)?n.classList.add("hidden"):n.classList.remove("hidden"))})}function C(){m("[data-remove-filter]").forEach(n=>{n.addEventListener("click",()=>{const r=n.dataset.removeFilter??"";d.delete(r),r==="type"&&(i.types=[]),r==="keyword"&&(i.q=""),r==="enabled"&&(i.enabled=null),k(),c()})}),m("[data-type]").forEach(n=>{n.addEventListener("change",()=>{i.types=m("[data-type]:checked").map(r=>r.dataset.type??"").filter(Boolean),c()})});const e=t("filter-q");e&&e.addEventListener("input",()=>{i.q=e.value,clearTimeout(e._t),e._t=setTimeout(c,300)});const a=t("filter-enabled");a&&a.addEventListener("change",()=>{const n=a.value;i.enabled=n==="all"?null:n==="enabled",c()})}m("[data-add-filter]").forEach(e=>{e.addEventListener("click",()=>{const a=e.dataset.addFilter??"";if(d.has(a))return;d.add(a);const n=e.closest("details");n&&(n.open=!1),k(),c()})});c();
