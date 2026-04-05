import { createContext, useContext, useState } from "react";

const KEY = "lurkr_admin_key";

const AdminContext = createContext({ isAdmin: false, unlock: () => {}, lock: () => {} });

export function AdminProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(() => !!sessionStorage.getItem(KEY));

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
