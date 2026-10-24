export const getToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("trademun_token");
};

export const setToken = (token: string) => {
  if (typeof window === "undefined") return;
  localStorage.setItem("trademun_token", token);
};

export const removeToken = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("trademun_token");
  localStorage.removeItem("trademun_user");
};

export const getUser = () => {
  if (typeof window === "undefined") return null;
  const user = localStorage.getItem("trademun_user");
  return user ? JSON.parse(user) : null;
};

export const setUser = (user: any) => {
  if (typeof window === "undefined") return;
  localStorage.setItem("trademun_user", JSON.stringify(user));
};