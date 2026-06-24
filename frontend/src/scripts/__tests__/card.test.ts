import { describe, it, expect } from "vitest";
import {
  entityCard,
  cardTitle,
  contextBadge,
  statusBadgeSoft,
  actionBtn,
  actionEdit,
  actionDisabled,
  copyBtn,
  metaChip,
  tagChips,
  urlRow,
  actionsWrap,
  metaWrap,
  errorBlock,
} from "~/scripts/card";
import { icon } from "~/scripts/icons";

describe("entityCard", () => {
  it("renderiza head, body y foot dentro de un .card", () => {
    const html = entityCard({ head: "HEAD", body: "BODY", foot: "FOOT" });
    expect(html).toContain("card");
    expect(html).toContain("HEAD");
    expect(html).toContain("BODY");
    expect(html).toContain("FOOT");
    expect(html).toContain("ent-card-head");
    expect(html).toContain("ent-card-body");
    expect(html).toContain("ent-card-foot");
  });

  it("omite el bloque body cuando está vacío", () => {
    const html = entityCard({ head: "H", body: "", foot: "F" });
    expect(html).not.toContain("ent-card-body");
    expect(html).toContain("ent-card-head");
    expect(html).toContain("ent-card-foot");
  });
});

describe("cardTitle", () => {
  it("renderiza el texto y un title con el mismo valor", () => {
    const html = cardTitle("Hola");
    expect(html).toContain("Hola");
    expect(html).toContain('title="Hola"');
  });

  it("trunca con clases de truncamiento", () => {
    const html = cardTitle("x");
    expect(html).toContain("truncate");
    expect(html).toContain("min-w-0");
  });

  it("escapa HTML peligroso en el texto visible", () => {
    const payload = '<script>alert(1)</script>';
    const html = cardTitle(payload);
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("escapa comillas en el atributo title (XSS de atributo)", () => {
    const payload = 'x" onmouseover="alert(1)';
    const html = cardTitle(payload);
    // Parseamos el HTML para inspeccionar los atributos reales del span.
    // El payload, al escaparse las comillas en title, no debe formar un
    // atributo onmouseover independiente.
    const div = document.createElement("div");
    div.innerHTML = html;
    const span = div.querySelector("span");
    expect(span).not.toBeNull();
    expect(span?.getAttribute("onmouseover")).toBeNull();
    // El title conserva el payload como texto (las comillas se decodifican
    // al leer el atributo, pero no se inyectan atributos nuevos).
    expect(span?.getAttribute("title")).toContain('"');
  });
});

describe("contextBadge", () => {
  it("sin icono renderiza solo el label", () => {
    const html = contextBadge(null, "fuente");
    expect(html).toContain("fuente");
    expect(html).not.toContain("<svg");
  });

  it("con icono renderiza el svg", () => {
    const html = contextBadge("edit", "lbl");
    expect(html).toContain("<svg");
    expect(html).toContain("lbl");
  });

  it("incluye title cuando se pasa", () => {
    const html = contextBadge("edit", "lbl", "tooltip");
    expect(html).toContain('title="tooltip"');
  });

  it("omite title cuando no se pasa", () => {
    const html = contextBadge("edit", "lbl");
    expect(html).not.toContain("title=");
  });

  it("escapa el label y el title", () => {
    const html = contextBadge(null, "<b>", '"><x>');
    expect(html).toContain("&lt;b&gt;");
    expect(html).not.toContain('"><x>');
  });
});

describe("statusBadgeSoft", () => {
  it("incluye la clase de color y el label", () => {
    const html = statusBadgeSoft("pendiente", "badge-warning");
    expect(html).toContain("badge-warning");
    expect(html).toContain("pendiente");
  });

  it("incluye un title descriptivo", () => {
    const html = statusBadgeSoft("pendiente", "badge-warning");
    expect(html).toContain('title="Estado pendiente"');
  });

  it("escapa el label en el title", () => {
    const html = statusBadgeSoft('<x>', "badge-warning");
    expect(html).toContain("&lt;x&gt;");
  });
});

describe("actionBtn", () => {
  it("ex pone data-action, data-id y aria-label", () => {
    const html = actionBtn("approve", "id_1", "check", "Aprobar");
    expect(html).toContain('data-action="approve"');
    expect(html).toContain('data-id="id_1"');
    expect(html).toContain('aria-label="Aprobar"');
    expect(html).toContain('title="Aprobar"');
    expect(html).toContain(icon("check", 16));
  });

  it("incluye clases extra cuando se pasan", () => {
    const html = actionBtn("x", "y", "check", "z", "text-info");
    expect(html).toContain("text-info");
  });

  it("escapa comillas en data-id y aria-label (XSS de atributo)", () => {
    const evilId = '"><script>alert(1)</script>';
    const html = actionBtn("x", evilId, "check", "y");
    expect(html).not.toContain('"><script>');
    expect(html).toContain("&quot;");
    expect(html).toContain("&lt;script&gt;");
  });
});

describe("actionEdit", () => {
  it("renderiza un <a> con href y aria-label", () => {
    const html = actionEdit("/seeds/edit?id=1", "Editar");
    expect(html.startsWith("<a ")).toBe(true);
    expect(html).toContain('href="/seeds/edit?id=1"');
    expect(html).toContain('aria-label="Editar"');
    expect(html).toContain('title="Editar"');
  });

  it("escapa el href", () => {
    const html = actionEdit('"><script>', "Editar");
    expect(html).not.toContain('"><script>');
    expect(html).toContain("&quot;");
  });
});

describe("actionDisabled", () => {
  it("marca aria-disabled y tabindex=-1", () => {
    const html = actionDisabled("check", "x", "no disponible");
    expect(html).toContain('aria-disabled="true"');
    expect(html).toContain('tabindex="-1"');
    expect(html).toContain('btn-disabled');
  });

  it("usa title con el reason y aria-label con el label", () => {
    const html = actionDisabled("check", "Aprobar", "no disponible");
    expect(html).toContain('aria-label="Aprobar"');
    expect(html).toContain('title="no disponible"');
  });
});

describe("copyBtn", () => {
  it("ex pone data-action=copy-url y data-url", () => {
    const html = copyBtn("https://example.com");
    expect(html).toContain('data-action="copy-url"');
    expect(html).toContain('data-url="https://example.com"');
    expect(html).toContain('aria-label="Copiar URL"');
  });

  it("escapa la URL en el atributo", () => {
    const html = copyBtn('"><x>');
    expect(html).not.toContain('"><x>');
    expect(html).toContain("&quot;");
  });
});

describe("metaChip", () => {
  it("renderiza el texto y la clase text-xs", () => {
    const html = metaChip("clock", "hace 2d");
    expect(html).toContain("text-xs");
    expect(html).toContain("hace 2d");
    expect(html).toContain(icon("clock", 12));
  });

  it("incluye title cuando se pasa", () => {
    const html = metaChip("clock", "t", "tooltip");
    expect(html).toContain('title="tooltip"');
  });

  it("omite title cuando no se pasa", () => {
    const html = metaChip("clock", "t");
    expect(html).not.toContain("title=");
  });
});

describe("tagChips", () => {
  it("devuelve cadena vacía para undefined o array vacío", () => {
    expect(tagChips(undefined)).toBe("");
    expect(tagChips([])).toBe("");
  });

  it("renderiza un badge por tag", () => {
    const html = tagChips(["a", "b", "c"]);
    const count = (html.match(/badge-sm/g) || []).length;
    expect(count).toBe(3);
    expect(html).toContain(">a<");
    expect(html).toContain(">b<");
    expect(html).toContain(">c<");
  });

  it("escapa el contenido del tag (XSS)", () => {
    const html = tagChips(['<script>alert(1)</script>']);
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).toContain("&lt;script&gt;");
  });
});

describe("urlRow", () => {
  it("extrae el hostname de una URL válida", () => {
    const html = urlRow("https://example.com/some/path");
    expect(html).toContain("example.com");
    expect(html).toContain('href="https://example.com/some/path"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it("cae al raw string cuando la URL es inválida", () => {
    const html = urlRow("not-a-url");
    // El dominio mostrado en el enlace es el raw (no se pudo parsear).
    expect(html).toContain(">not-a-url<");
    expect(html).toContain('href="not-a-url"');
    // No se extrajo un hostname distinto.
    expect(html).not.toContain(">localhost<");
    expect(html).not.toContain(">example.com<");
  });

  it("incluye un botón de copiar", () => {
    const html = urlRow("https://example.com");
    expect(html).toContain('data-action="copy-url"');
  });
});

describe("actionsWrap / metaWrap", () => {
  it("actionsWrap envuelve en un div flex con ml-auto", () => {
    const html = actionsWrap("INNER");
    expect(html.startsWith("<div")).toBe(true);
    expect(html).toContain("ml-auto");
    expect(html).toContain("INNER");
  });

  it("metaWrap envuelve en un div flex", () => {
    const html = metaWrap("INNER");
    expect(html.startsWith("<div")).toBe(true);
    expect(html).toContain("INNER");
  });
});

describe("errorBlock", () => {
  it("devuelve cadena vacía para null/undefined/cadena vacía", () => {
    expect(errorBlock(null)).toBe("");
    expect(errorBlock(undefined)).toBe("");
    expect(errorBlock("")).toBe("");
  });

  it("renderiza un alert-error con el mensaje y role=alert", () => {
    const html = errorBlock("403 Forbidden");
    expect(html).toContain("alert-error");
    expect(html).toContain('role="alert"');
    expect(html).toContain("403 Forbidden");
  });

  it("respeta saltos de línea con whitespace-pre-line", () => {
    const html = errorBlock("línea 1\nlínea 2");
    expect(html).toContain("whitespace-pre-line");
    expect(html).toContain("línea 1");
    expect(html).toContain("línea 2");
  });

  it("escapa HTML peligroso (XSS)", () => {
    const html = errorBlock('<script>alert(1)</script>');
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).toContain("&lt;script&gt;");
  });
});
