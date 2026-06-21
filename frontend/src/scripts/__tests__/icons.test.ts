import { describe, it, expect } from "vitest";
import { icon, iconPath, ICON_NAMES } from "~/scripts/icons";

describe("iconPath", () => {
  it("devuelve el path SVG para un icono existente", () => {
    const p = iconPath("edit");
    expect(typeof p).toBe("string");
    expect(p.length).toBeGreaterThan(0);
    expect(p).toContain("<path");
  });

  it("devuelve cadena vacía para un icono inexistente", () => {
    expect(iconPath("nonexistent-icon")).toBe("");
  });

  it("es estable para varias llamadas", () => {
    expect(iconPath("copy")).toBe(iconPath("copy"));
  });
});

describe("icon", () => {
  it("renderiza un svg con el size por defecto (16)", () => {
    const svg = icon("edit");
    expect(svg).toContain("<svg");
    expect(svg).toContain('width="16"');
    expect(svg).toContain('height="16"');
    expect(svg).toContain('viewBox="0 0 24 24"');
    expect(svg).toContain("aria-hidden=\"true\"");
    expect(svg).toContain("focusable=\"false\"");
  });

  it("respeta un size personalizado", () => {
    const svg = icon("edit", 24);
    expect(svg).toContain('width="24"');
    expect(svg).toContain('height="24"');
  });

  it("incluye la clase cuando se pasa cls", () => {
    const svg = icon("edit", 16, "my-class");
    expect(svg).toContain('class="my-class"');
  });

  it("no incluye el atributo class cuando no se pasa cls", () => {
    const svg = icon("edit");
    expect(svg).not.toContain("class=");
  });

  it("devuelve cadena vacía para un icono inexistente", () => {
    expect(icon("nonexistent", 16)).toBe("");
  });

  it("incrusta el path del icono", () => {
    const svg = icon("trash");
    expect(svg).toContain(iconPath("trash"));
  });
});

describe("ICON_NAMES", () => {
  it("es un array no vacío", () => {
    expect(Array.isArray(ICON_NAMES)).toBe(true);
    expect(ICON_NAMES.length).toBeGreaterThan(0);
  });

  it("contiene los iconos clave usados en la UI", () => {
    expect(ICON_NAMES).toContain("edit");
    expect(ICON_NAMES).toContain("trash");
    expect(ICON_NAMES).toContain("copy");
    expect(ICON_NAMES).toContain("check");
  });

  it("no contiene duplicados", () => {
    expect(new Set(ICON_NAMES).size).toBe(ICON_NAMES.length);
  });
});
