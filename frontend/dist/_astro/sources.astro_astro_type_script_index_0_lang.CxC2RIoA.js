const r="http://localhost:8000/api";let m=null;const h=document.getElementById("error-msg");function u(t){h.textContent=t,h.classList.remove("hidden")}function g(){h.classList.add("hidden")}async function p(t){try{const e=await t.json();return Array.isArray(e.detail)?e.detail[0]?.msg||"Request failed":e.detail||"Request failed"}catch{return"Request failed"}}async function E(){g();const e=await(await fetch(`${r}/sources`)).json(),a=document.getElementById("sources-list");if(!e.length){a.innerHTML='<p class="text-sm text-base-content/40">No sources configured. Add one to get started.</p>';return}a.innerHTML=`<div class="overflow-x-auto"><table class="table table-zinc">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>URL</th>
            <th>Priority</th>
            <th>Tags</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${e.map(n=>`
          <tr>
            <td class="font-medium">${l(n.name)}</td>
            <td><span class="badge badge-sm">${l(n.source_type)}</span></td>
            <td class="text-sm text-base-content/60 max-w-[220px] truncate">${l(n.url)}</td>
            <td><span class="badge badge-sm badge-ghost">${n.priority}</span></td>
            <td>${(n.tags||[]).map(c=>`<span class="badge badge-sm badge-outline mr-1">${l(c)}</span>`).join("")}</td>
            <td><div class="flex gap-1"><button class="btn btn-ghost btn-xs" data-action="edit" data-id="${n.id}">Edit</button><button class="btn btn-ghost btn-xs text-error" data-action="delete" data-id="${n.id}">Delete</button></div></td>
          </tr>`).join("")}</tbody>
      </table></div>`}function l(t){if(!t)return"";const e=document.createElement("div");return e.appendChild(document.createTextNode(t)),e.innerHTML}function f(t){m=t?t.id:null,document.getElementById("form-title").textContent=t?"Edit Source":"Add Source",document.getElementById("modal-save").textContent=t?"Update":"Save",document.getElementById("src-name").value=t?t.name:"",document.getElementById("src-type").value=t?t.source_type:"rss",document.getElementById("src-url").value=t?t.url:"",document.getElementById("src-priority").value=t?String(t.priority):"2",document.getElementById("src-tags").value=t?(t.tags||[]).join(", "):"",document.getElementById("form-modal").showModal()}document.getElementById("sources-list").addEventListener("click",async t=>{const e=t.target.closest("[data-action]");if(!e)return;g();const a=e.dataset.id;if(e.dataset.action==="delete"){if(!(await fetch(`${r}/sources/${a}`,{method:"DELETE"})).ok){u("Failed to delete source");return}E()}else if(e.dataset.action==="edit"){const n=await fetch(`${r}/sources/${a}`);if(!n.ok){u("Failed to load source");return}f(await n.json())}});document.getElementById("btn-add").addEventListener("click",()=>{g(),f(null)});document.getElementById("modal-cancel").addEventListener("click",()=>{document.getElementById("form-modal").close()});document.getElementById("modal-save").addEventListener("click",async()=>{const t=document.getElementById("src-name").value.trim(),e=document.getElementById("src-type").value,a=document.getElementById("src-url").value.trim(),n=parseInt(document.getElementById("src-priority").value),c=document.getElementById("src-tags").value.trim();if(!t||!a){u("Name and URL are required.");return}const o=document.getElementById("modal-save");o.disabled=!0;const b=o.textContent;o.textContent="Saving...",g();try{const i=c?c.split(",").map(d=>d.trim()):[];if(m){const d=new URLSearchParams({name:t,source_type:e,url:a,priority:String(n)});i.forEach(y=>d.append("tags",y));const s=await fetch(`${r}/sources/${m}?${d}`,{method:"PATCH"});if(!s.ok)throw new Error(await p(s))}else{const d=new URLSearchParams({name:t,source_type:e,url:a,priority:String(n)});i.forEach(y=>d.append("tags",y));const s=await fetch(`${r}/sources?${d}`,{method:"POST"});if(!s.ok)throw new Error(await p(s))}document.getElementById("form-modal").close(),m=null,["src-name","src-url","src-tags"].forEach(d=>document.getElementById(d).value=""),E()}catch(i){u("Error: "+i.message)}finally{o.disabled=!1,o.textContent=b}});E();
