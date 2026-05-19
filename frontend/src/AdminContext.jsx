import { createContext, useContext, useState, useEffect } from "react";
import { api } from "./api";

const KEY = "spl_admin_key";

const AdminContext = createContext({ isAdmin: false, unlock: () => {}, lock: () => {} });

export function AdminProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(() => !!sessionStorage.getItem(KEY));

  // Re-verify any stored key on mount — a wrong key from a stale session shouldn't
  // leave the UI in admin mode while every admin request silently 401s.
  useEffect(() => {
    const stored = sessionStorage.getItem(KEY);
    if (!stored) return;
    api.adminCheck(stored).catch(() => {
      sessionStorage.removeItem(KEY);
      setIsAdmin(false);
    });
  }, []);

  const unlock = (key) => {
    sessionStorage.setItem(KEY, key);
    setIsAdmin(true);
  };

  const lock = () => {
    sessionStorage.removeItem(KEY);
    setIsAdmin(false);
  };

  return (
    <AdminContext.Provider value={{ isAdmin, unlock, lock }}>
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin() {
  return useContext(AdminContext);
}

export function getAdminKey() {
  return import.meta.env.VITE_ADMIN_KEY || sessionStorage.getItem(KEY) || "";
}
