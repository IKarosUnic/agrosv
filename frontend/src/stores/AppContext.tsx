import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { loadPrefs, savePrefs, getLastSyncTimestamp } from "../services/offline/storage";
import { syncQueuedFieldObservations } from "../services/offline/sync";

export type ThemeMode = "light" | "dark" | "system";
export type UserRoleProfile = "farmer" | "technician" | "researcher" | "institutional";

export interface SelectedLocation {
  lat: number;
  lon: number;
  label: string;
  departmentCode?: string;
  departmentName?: string;
  municipalityName?: string;
}

export interface PersistedPrefs {
  theme: ThemeMode;
  roleProfile: UserRoleProfile;
  simpleMode: boolean;
  areaUnit: "mz" | "ha";
  selectedLocation: SelectedLocation;
  selectedCropId: string;
}

const DEFAULT_PREFS: PersistedPrefs = {
  theme: "system",
  roleProfile: "farmer",
  simpleMode: true,
  areaUnit: "mz",
  selectedLocation: {
    lat: 13.6894,
    lon: -89.1872,
    label: "San Salvador (centro de referencia)",
    departmentCode: "SLV-SS",
    departmentName: "San Salvador",
  },
  selectedCropId: "maize",
};

interface AppContextValue {
  theme: ThemeMode;
  resolvedTheme: "light" | "dark";
  setTheme: (t: ThemeMode) => void;
  roleProfile: UserRoleProfile;
  setRoleProfile: (r: UserRoleProfile) => void;
  simpleMode: boolean;
  setSimpleMode: (v: boolean) => void;
  areaUnit: "mz" | "ha";
  setAreaUnit: (u: "mz" | "ha") => void;
  selectedLocation: SelectedLocation;
  setSelectedLocation: (loc: SelectedLocation) => void;
  selectedCropId: string;
  setSelectedCropId: (id: string) => void;
  isOnline: boolean;
  lastSyncAt: string | null;
  refreshLastSync: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

function resolveSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [prefs, setPrefs] = useState<PersistedPrefs>(() => ({
    ...DEFAULT_PREFS,
    ...loadPrefs<Partial<PersistedPrefs>>({}),
  }));
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(resolveSystemTheme);
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(() => getLastSyncTimestamp());

  useEffect(() => {
    savePrefs(prefs);
  }, [prefs]);

  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = (e: MediaQueryListEvent) => setSystemTheme(e.matches ? "dark" : "light");
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, []);

  const resolvedTheme = prefs.theme === "system" ? systemTheme : prefs.theme;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", resolvedTheme);
  }, [resolvedTheme]);

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      syncQueuedFieldObservations().catch(() => undefined);
    };
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const setTheme = useCallback((theme: ThemeMode) => {
    setPrefs((p) => ({ ...p, theme }));
  }, []);

  const setRoleProfile = useCallback((roleProfile: UserRoleProfile) => {
    setPrefs((p) => ({
      ...p,
      roleProfile,
      simpleMode: roleProfile === "farmer",
    }));
  }, []);

  const setSimpleMode = useCallback((simpleMode: boolean) => {
    setPrefs((p) => ({ ...p, simpleMode }));
  }, []);

  const setAreaUnit = useCallback((areaUnit: "mz" | "ha") => {
    setPrefs((p) => ({ ...p, areaUnit }));
  }, []);

  const setSelectedLocation = useCallback((selectedLocation: SelectedLocation) => {
    setPrefs((p) => ({ ...p, selectedLocation }));
  }, []);

  const setSelectedCropId = useCallback((selectedCropId: string) => {
    setPrefs((p) => ({ ...p, selectedCropId }));
  }, []);

  const refreshLastSync = useCallback(() => {
    setLastSyncAt(getLastSyncTimestamp());
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({
      theme: prefs.theme,
      resolvedTheme,
      setTheme,
      roleProfile: prefs.roleProfile,
      setRoleProfile,
      simpleMode: prefs.simpleMode,
      setSimpleMode,
      areaUnit: prefs.areaUnit,
      setAreaUnit,
      selectedLocation: prefs.selectedLocation,
      setSelectedLocation,
      selectedCropId: prefs.selectedCropId,
      setSelectedCropId,
      isOnline,
      lastSyncAt,
      refreshLastSync,
    }),
    [
      prefs,
      resolvedTheme,
      setTheme,
      setRoleProfile,
      setSimpleMode,
      setAreaUnit,
      setSelectedLocation,
      setSelectedCropId,
      isOnline,
      lastSyncAt,
      refreshLastSync,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp debe usarse dentro de AppProvider");
  return ctx;
}
