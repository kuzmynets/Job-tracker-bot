import Link from "next/link";
import { getVacancies, STATUSES, STATUS_LABELS, type Status } from "../lib/vacancies";

export const dynamic = "force-dynamic"; // завжди свіжі дані з Supabase

const dateFormat = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "short" });

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const active = STATUSES.includes(status as Status) ? (status as Status) : null;

  const all = await getVacancies();
  const rows = active ? all.filter((v) => v.status === active) : all;
  const count = (s: Status) => all.filter((v) => v.status === s).length;

  return (
    <main>
      <header>
        <h1>Job Tracker</h1>
        <p>Вакансії, які розібрав і зберіг Telegram-бот.</p>
      </header>

      <nav aria-label="Фільтр за статусом">
        <Link href="/" className={active ? "tab" : "tab on"}>
          Усі <span>{all.length}</span>
        </Link>
        {STATUSES.map((s) => (
          <Link key={s} href={`/?status=${s}`} className={active === s ? "tab on" : "tab"}>
            {STATUS_LABELS[s]} <span>{count(s)}</span>
          </Link>
        ))}
      </nav>

      {rows.length === 0 ? (
        <p className="empty">Тут поки порожньо.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Роль</th>
              <th>Компанія</th>
              <th>Стек</th>
              <th>Зарплата</th>
              <th>Формат</th>
              <th>Рівень</th>
              <th>Статус</th>
              <th>Додано</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id}>
                <td data-label="Роль" className="role">
                  {v.url ? (
                    <a href={v.url} target="_blank" rel="noopener noreferrer">
                      {v.role ?? "—"}
                    </a>
                  ) : (
                    v.role ?? "—"
                  )}
                </td>
                <td data-label="Компанія">{v.company ?? "—"}</td>
                <td data-label="Стек">
                  <div className="chips">
                    {v.stack.length ? v.stack.map((t) => <span key={t}>{t}</span>) : "—"}
                  </div>
                </td>
                <td data-label="Зарплата">{v.salary ?? "—"}</td>
                <td data-label="Формат">{v.work_format ?? "—"}</td>
                <td data-label="Рівень">{v.level ?? "—"}</td>
                <td data-label="Статус">
                  <span className={`status ${v.status}`}>{STATUS_LABELS[v.status]}</span>
                </td>
                <td data-label="Додано">{dateFormat.format(new Date(v.created_at))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
