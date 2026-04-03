export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError((data as { detail?: string }).detail ?? "Unexpected API error", response.status);
  }
  return data as T;
}

async function readError(response: Response): Promise<never> {
  const data = await response.json().catch(() => ({}));
  throw new ApiError((data as { detail?: string }).detail ?? "Unexpected API error", response.status);
}

function readCookie(name: string): string | null {
  const cookie = document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(`${name}=`));

  if (!cookie) {
    return null;
  }
  return decodeURIComponent(cookie.slice(name.length + 1));
}

function csrfHeaders(): Record<string, string> {
  const csrfToken = readCookie("trailforge_csrf");
  if (!csrfToken) {
    return {};
  }
  return { "X-CSRF-Token": csrfToken };
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "include"
  });
  return readResponse<T>(response);
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...csrfHeaders()
    },
    body: JSON.stringify(payload),
    credentials: "include"
  });
  return readResponse<T>(response);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      ...csrfHeaders()
    },
    body: formData,
    credentials: "include"
  });
  return readResponse<T>(response);
}

export async function apiPostFormWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress: (percent: number) => void
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", path, true);
    request.withCredentials = true;

    const headers = csrfHeaders();
    Object.entries(headers).forEach(([key, value]) => {
      request.setRequestHeader(key, value);
    });

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable || event.total <= 0) return;
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      onProgress(percent);
    };

    request.onerror = () => {
      reject(new ApiError("Network error", 0));
    };

    request.onload = () => {
      const status = request.status;
      const text = request.responseText || "";
      const parsed = text
        ? (() => {
            try {
              return JSON.parse(text);
            } catch {
              return {};
            }
          })()
        : {};

      if (status >= 200 && status < 300) {
        onProgress(100);
        resolve(parsed as T);
        return;
      }

      reject(new ApiError((parsed as { detail?: string }).detail ?? "Unexpected API error", status));
    };

    request.send(formData);
  });
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "DELETE",
    headers: {
      ...csrfHeaders()
    },
    credentials: "include"
  });
  return readResponse<T>(response);
}

export async function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...csrfHeaders()
    },
    body: JSON.stringify(payload),
    credentials: "include"
  });
  return readResponse<T>(response);
}

export async function apiGetRaw(path: string): Promise<Response> {
  const response = await fetch(path, {
    credentials: "include"
  });
  if (!response.ok) {
    return readError(response);
  }
  return response;
}
