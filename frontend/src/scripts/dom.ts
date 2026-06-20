import type { ApiError } from "./types";

/**
 * Obtiene un elemento por id asumiendo que existe en el markup estático del
 * propio componente (el script se ejecuta tras el parseo del DOM). Centraliza
 * la aserción no-nula para satisfacer `strict` sin sembrar `!` por todo el código.
 */
export function byId<T extends HTMLElement = HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

/** querySelector tipado. */
export function q<T extends Element = HTMLElement>(selector: string): T | null {
  return document.querySelector<T>(selector);
}

/** querySelectorAll tipado y devuelto como array. */
export function qAll<T extends Element = HTMLElement>(selector: string): T[] {
  return Array.from(document.querySelectorAll<T>(selector));
}

/** Lee el mensaje de error de una respuesta de la API. */
export async function getErrorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as ApiError;
    if (Array.isArray(body.detail)) return body.detail[0]?.msg || "Request failed";
    return body.detail || "Request failed";
  } catch {
    return "Request failed";
  }
}

/** Escapa texto para incrustarlo de forma segura en HTML. */
export function esc(str: string | null | undefined): string {
  if (!str) return "";
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(str));
  return d.innerHTML;
}

/** Igual que `esc` pero además escapa comillas dobles para atributos. */
export function escAttr(str: string | null | undefined): string {
  return esc(str).replace(/"/g, "&quot;");
}

declare global {
  interface HTMLInputElement {
    _t?: ReturnType<typeof setTimeout>;
  }
  interface HTMLTextAreaElement {
    _t?: ReturnType<typeof setTimeout>;
  }
}
