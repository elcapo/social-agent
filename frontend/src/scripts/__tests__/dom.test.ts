import { describe, it, expect, beforeEach } from "vitest";
import { byId, q, qAll, getErrorMessage, esc, escAttr } from "~/scripts/dom";

describe("byId", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("devuelve el elemento cuando existe", () => {
    const el = document.createElement("div");
    el.id = "foo";
    document.body.appendChild(el);
    const got = byId("foo");
    expect(got).toBe(el);
  });

  it("soporta tipado genérico", () => {
    const input = document.createElement("input");
    input.id = "in";
    document.body.appendChild(input);
    const got = byId<HTMLInputElement>("in");
    expect(got.tagName).toBe("INPUT");
  });
});

describe("q", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("devuelve el primer match", () => {
    document.body.innerHTML = '<a class="x">1</a><a class="x">2</a>';
    const got = q<HTMLAnchorElement>(".x");
    expect(got).not.toBeNull();
    expect(got?.textContent).toBe("1");
  });

  it("devuelve null cuando no hay match", () => {
    expect(q(".nope")).toBeNull();
  });
});

describe("qAll", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("devuelve un array con todos los matches", () => {
    document.body.innerHTML = '<a class="x">1</a><a class="x">2</a><a class="x">3</a>';
    const got = qAll(".x");
    expect(Array.isArray(got)).toBe(true);
    expect(got).toHaveLength(3);
  });

  it("devuelve un array vacío sin matches", () => {
    expect(qAll(".nope")).toEqual([]);
  });
});

describe("getErrorMessage", () => {
  it("extrae detail como string", async () => {
    const res = new Response(JSON.stringify({ detail: "boom" }), {
      headers: { "Content-Type": "application/json" },
    });
    expect(await getErrorMessage(res)).toBe("boom");
  });

  it("extrae el msg del primer elemento cuando detail es un array", async () => {
    const res = new Response(
      JSON.stringify({ detail: [{ msg: "invalid field" }, { msg: "second" }] }),
      { headers: { "Content-Type": "application/json" } }
    );
    expect(await getErrorMessage(res)).toBe("invalid field");
  });

  it("cae al fallback cuando detail es un array vacío", async () => {
    const res = new Response(JSON.stringify({ detail: [] }), {
      headers: { "Content-Type": "application/json" },
    });
    expect(await getErrorMessage(res)).toBe("Request failed");
  });

  it("cae al fallback cuando el body no es JSON", async () => {
    const res = new Response("not-json", {
      headers: { "Content-Type": "text/plain" },
    });
    expect(await getErrorMessage(res)).toBe("Request failed");
  });

  it("cae al fallback cuando detail falta", async () => {
    const res = new Response(JSON.stringify({ other: "x" }), {
      headers: { "Content-Type": "application/json" },
    });
    expect(await getErrorMessage(res)).toBe("Request failed");
  });
});

describe("esc", () => {
  it("escapa <, > y &", () => {
    expect(esc("<b>")).toBe("&lt;b&gt;");
    expect(esc("a & b")).toBe("a &amp; b");
  });

  it("no escapa comillas (es para texto, no atributos)", () => {
    expect(esc('a "b"')).toBe('a "b"');
  });

  it("devuelve cadena vacía para null/undefined/cadena vacía", () => {
    expect(esc(null)).toBe("");
    expect(esc(undefined)).toBe("");
    expect(esc("")).toBe("");
  });

  it("neutraliza un payload XSS típico en texto", () => {
    const payload = '<script>alert(1)</script>';
    const escaped = esc(payload);
    expect(escaped).not.toContain("<script>");
    expect(escaped).not.toContain("</script>");
    expect(escaped).toContain("&lt;script&gt;");
  });
});

describe("escAttr", () => {
  it("escapa comillas dobles para uso seguro en atributos", () => {
    expect(escAttr('a "b"')).toBe("a &quot;b&quot;");
  });

  it("escapa < y > además de comillas", () => {
    expect(escAttr('"><img src=x>')).not.toContain('"><');
  });

  it("devuelve cadena vacía para null/undefined", () => {
    expect(escAttr(null)).toBe("");
    expect(escAttr(undefined)).toBe("");
  });

  it("neutraliza un payload XSS de atributo", () => {
    const payload = 'x"><script>alert(1)</script>';
    const escaped = escAttr(payload);
    expect(escaped).not.toContain('"><script>');
    expect(escaped).toContain("&quot;");
    expect(escaped).toContain("&lt;script&gt;");
  });
});
