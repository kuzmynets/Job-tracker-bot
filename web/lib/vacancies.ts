import { createClient } from "@supabase/supabase-js";

export const STATUSES = ["new", "applied", "interview", "rejected"] as const;
export type Status = (typeof STATUSES)[number];

export const STATUS_LABELS: Record<Status, string> = {
  new: "Нова",
  applied: "Відгукнувся",
  interview: "Співбесіда",
  rejected: "Відмова",
};

export type Vacancy = {
  id: number;
  created_at: string;
  company: string | null;
  role: string | null;
  stack: string[];
  salary: string | null;
  work_format: string | null;
  level: string | null;
  status: Status;
  url: string | null;
};

// Виконується лише на сервері, тому ключ не потрапляє в браузер.
export async function getVacancies(): Promise<Vacancy[]> {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;
  if (!url || !key) {
    throw new Error("Не задано SUPABASE_URL або SUPABASE_KEY");
  }
  const supabase = createClient(url, key, { auth: { persistSession: false } });
  const { data, error } = await supabase
    .from("vacancies")
    .select("id, created_at, company, role, stack, salary, work_format, level, status, url")
    .order("created_at", { ascending: false })
    .limit(500);
  if (error) throw new Error(error.message);
  return (data ?? []) as Vacancy[];
}
