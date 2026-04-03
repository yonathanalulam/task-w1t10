import { describe, expect, it, vi } from "vitest";

import { apiPatch, apiPost, apiPostForm, apiPostFormWithProgress } from "../../src/api/client";

describe("api client csrf behavior", () => {
  it("sends csrf header on mutation calls", async () => {
    document.cookie = "trailforge_csrf=test-csrf-token";

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await apiPost("/api/example", { x: 1 });
    await apiPatch("/api/example", { y: 2 });
    const formData = new FormData();
    formData.append("file", new Blob(["test"], { type: "text/plain" }), "sample.txt");
    await apiPostForm("/api/example/upload", formData);

    expect(fetchSpy).toHaveBeenCalledTimes(3);
    for (const [, options] of fetchSpy.mock.calls) {
      const headers = options?.headers as Record<string, string>;
      expect(headers["X-CSRF-Token"]).toBe("test-csrf-token");
    }
  });
});

describe("api client multipart upload progress", () => {
  it("reports progress and parses successful response", async () => {
    document.cookie = "trailforge_csrf=test-csrf-token";

    class FakeXHR {
      static instance: FakeXHR;
      method = "";
      url = "";
      withCredentials = false;
      status = 201;
      responseText = JSON.stringify({ ok: true });
      headers: Record<string, string> = {};
      upload: { onprogress: ((event: ProgressEvent<EventTarget>) => void) | null } = { onprogress: null };
      onerror: (() => void) | null = null;
      onload: (() => void) | null = null;

      constructor() {
        FakeXHR.instance = this;
      }

      open(method: string, url: string) {
        this.method = method;
        this.url = url;
      }

      setRequestHeader(key: string, value: string) {
        this.headers[key] = value;
      }

      send(_: FormData) {
        this.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 } as ProgressEvent<EventTarget>);
        this.onload?.();
      }
    }

    const originalXHR = global.XMLHttpRequest;
    vi.stubGlobal("XMLHttpRequest", FakeXHR as unknown as typeof XMLHttpRequest);

    const formData = new FormData();
    formData.append("file", new Blob(["hello"]), "hello.csv");
    const updates: number[] = [];
    const result = await apiPostFormWithProgress<{ ok: boolean }>("/api/upload", formData, (percent) => updates.push(percent));

    expect(result.ok).toBe(true);
    expect(updates).toEqual([50, 100]);
    expect(FakeXHR.instance.method).toBe("POST");
    expect(FakeXHR.instance.url).toBe("/api/upload");
    expect(FakeXHR.instance.headers["X-CSRF-Token"]).toBe("test-csrf-token");
    expect(FakeXHR.instance.withCredentials).toBe(true);

    vi.stubGlobal("XMLHttpRequest", originalXHR);
  });
});
