/* Клиент API v1: токен в заголовке Authorization, ответы только JSON. */
const BASE = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");
const KEY = "fc_token";

export const tokenStore = {
  get() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } },
  set(t) { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch (e) { /* приватный режим */ } },
};

export const hooks = { onUnauthorized: null };

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function request(method, path, body, opts = {}) {
  const headers = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = "Bearer " + token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (e) {
    throw new ApiError("Нет связи с сервером.", 0);
  }
  let data = null;
  try { data = await res.json(); } catch (e) { /* пустой ответ */ }
  if (res.status === 401 && !opts.quiet401) {
    if (hooks.onUnauthorized) hooks.onUnauthorized();
  }
  if (!res.ok) throw new ApiError((data && data.error) || "Ошибка сервера (" + res.status + ").", res.status);
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body || {}),
  put: (path, body) => request("PUT", path, body || {}),
  del: (path) => request("DELETE", path),
  // вход и регистрация: 401 здесь значит «неверный пароль», а не «токен протух»
  auth: (path, body) => request("POST", path, body, { quiet401: true }),
};
