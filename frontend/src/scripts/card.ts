import { icon } from "./icons";
import { esc, escAttr } from "./dom";

export interface CardParts {
  head: string;
  body: string;
  foot: string;
}

export function entityCard(parts: CardParts): string {
  return `<article class="card bg-base-100 border border-base-300 shadow-sm">
  <div class="card-body p-4 gap-2">
    <div class="ent-card-head flex items-center gap-2 flex-wrap">${parts.head}</div>
    ${parts.body ? `<div class="ent-card-body text-sm text-base-content/70 space-y-1.5">${parts.body}</div>` : ""}
    <div class="ent-card-foot flex items-center justify-between gap-2 flex-wrap pt-2 border-t border-base-200">${parts.foot}</div>
  </div>
</article>`;
}

export function cardTitle(text: string): string {
  return `<span class="font-medium truncate flex-1 min-w-0" title="${escAttr(text)}">${esc(text)}</span>`;
}

export function contextBadge(iconName: string | null, label: string, title?: string): string {
  const iconSvg = iconName ? icon(iconName, 12) : "";
  const titleAttr = title ? ` title="${escAttr(title)}"` : "";
  return `<span class="badge badge-sm badge-soft shrink-0 gap-1"${titleAttr}>${iconSvg}${esc(label)}</span>`;
}

export function statusBadgeSoft(label: string, color: string): string {
  return `<span class="badge badge-sm badge-soft ${color} shrink-0 ml-auto" title="Estado ${escAttr(label)}">${esc(label)}</span>`;
}

export function actionBtn(
  action: string,
  id: string,
  iconName: string,
  label: string,
  cls = ""
): string {
  return `<button class="btn btn-square btn-ghost btn-sm ${cls}" data-action="${action}" data-id="${escAttr(id)}" aria-label="${escAttr(label)}" title="${escAttr(label)}">${icon(iconName, 16)}</button>`;
}

export function actionEdit(href: string, label: string): string {
  return `<a href="${escAttr(href)}" class="btn btn-square btn-ghost btn-sm" aria-label="${escAttr(label)}" title="${escAttr(label)}">${icon("edit", 16)}</a>`;
}

export function actionDisabled(iconName: string, label: string, reason: string): string {
  return `<button class="btn btn-square btn-ghost btn-sm btn-disabled" tabindex="-1" aria-disabled="true" aria-label="${escAttr(label)}" title="${escAttr(reason)}">${icon(iconName, 16)}</button>`;
}

export function copyBtn(url: string): string {
  return `<button class="btn btn-square btn-ghost btn-xs shrink-0" data-action="copy-url" data-url="${escAttr(url)}" aria-label="Copiar URL" title="Copiar URL">${icon("copy", 14)}</button>`;
}

export function metaChip(iconName: string, text: string, title?: string): string {
  const titleAttr = title ? ` title="${escAttr(title)}"` : "";
  return `<span class="inline-flex items-center gap-1 text-xs text-base-content/60"${titleAttr}>${icon(iconName, 12)} ${esc(text)}</span>`;
}

export function tagChips(tags: string[] | undefined): string {
  if (!tags || !tags.length) return "";
  return `<div class="flex flex-wrap gap-1">${tags
    .map((t) => `<span class="badge badge-sm badge-soft badge-primary">${esc(t)}</span>`)
    .join("")}</div>`;
}

export function urlRow(url: string): string {
  let domain = url;
  try {
    domain = new URL(url).hostname;
  } catch {
    domain = url;
  }
  return `<div class="flex items-center gap-1 min-w-0">
    <a href="${escAttr(url)}" target="_blank" rel="noopener noreferrer" class="truncate hover:text-primary transition-colors" title="${escAttr(url)}">${esc(domain)}</a>
    ${copyBtn(url)}
  </div>`;
}

export function actionsWrap(actions: string): string {
  return `<div class="flex gap-1 ml-auto shrink-0">${actions}</div>`;
}

export function metaWrap(meta: string): string {
  return `<div class="flex items-center gap-3 flex-wrap min-w-0">${meta}</div>`;
}

export function errorBlock(msg: string | null | undefined): string {
  if (!msg) return "";
  return `<div class="alert alert-error py-2 px-3 text-xs gap-1.5" role="alert" aria-live="polite">${icon("circle-x", 14)} <span class="whitespace-pre-line break-words">${esc(msg)}</span></div>`;
}
