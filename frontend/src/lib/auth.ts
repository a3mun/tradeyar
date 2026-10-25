export const getToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("trademun_token");
};

export const setToken = (token: string) => {
  localStorage.setItem("trademun_token", token);
  // ⬅️ ذخیره در کوکی برای middleware
  document.cookie = `trademun_token=${token}; path=/; max-age=604800`; // ۷ روز
};

export const removeToken = () => {
  localStorage.removeItem("trademun_token");
  localStorage.removeItem("trademun_user");
  document.cookie = "trademun_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
};

export const getUser = () => {
  if (typeof window === "undefined") return null;
  const user = localStorage.getItem("trademun_user");
  return user ? JSON.parse(user) : null;
};

export const setUser = (user: any) => {
  localStorage.setItem("trademun_user", JSON.stringify(user));
};