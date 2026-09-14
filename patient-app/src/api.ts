import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

export type Provider = {
  id: string;
  name: string;
  specialty: string;
  initials: string;
  hospital: string;
  area: string;
  experience: string;
  fee: number;
  color: string;
};
export type Appointment = {
  id: string;
  provider: Provider;
  slot: string;
  status: "booked" | "checked_in" | "ready" | "completed" | "cancelled";
  token: string;
  created_at: string;
  demo: boolean;
};
export type Queue = {
  appointment: Appointment;
  ahead: number;
  estimated_minutes: number;
  position: number;
  demo: boolean;
  message: string;
};
export type Slot = { value: string; available: boolean };
const host =
  Platform.OS === "web" && typeof window !== "undefined"
    ? window.location.hostname
    : "127.0.0.1";
export const API_URL = process.env.EXPO_PUBLIC_API_URL || `http://${host}:8001`;
const key = "carelane-demo-session-v1";
let sessionPromise: Promise<string> | null = null;

async function raw(path: string, options: RequestInit = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(API_URL + path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
    const data = await response.json();
    if (!response.ok) {
      throw Object.assign(
        new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Please check your entries and try again.",
        ),
        { status: response.status },
      );
    }
    return data;
  } catch (error: any) {
    if (error.status) throw error;
    throw new Error(
      "We could not reach the demo service. Check that the app backend is running, then try again.",
    );
  } finally {
    clearTimeout(timer);
  }
}

function session(): Promise<string> {
  if (!sessionPromise)
    sessionPromise = (async () => {
      const saved = await AsyncStorage.getItem(key);
      if (saved) return saved;
      const result = await raw("/api/session", { method: "POST" });
      await AsyncStorage.setItem(key, result.token);
      return result.token as string;
    })().catch((error) => {
      sessionPromise = null;
      throw error;
    });
  return sessionPromise;
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  retry = true,
): Promise<T> {
  const token = await session();
  try {
    return await raw(path, {
      method,
      headers: { Authorization: `Bearer ${token}` },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch (error: any) {
    if (error.status === 401 && retry) {
      await AsyncStorage.removeItem(key);
      sessionPromise = null;
      return api(path, method, body, false);
    }
    throw error;
  }
}
export const newRequestId = () =>
  `visit-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
