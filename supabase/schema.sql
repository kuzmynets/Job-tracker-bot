-- Виконай у Supabase: SQL Editor -> New query -> Run
create table if not exists public.vacancies (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  user_id bigint not null,
  company text,
  role text,
  stack text[] not null default '{}',
  salary text,
  work_format text,
  level text,
  status text not null default 'new'
    check (status in ('new', 'applied', 'interview', 'rejected')),
  status_updated_at timestamptz not null default now(),
  url text,
  raw_text text
);

create index if not exists vacancies_user_created_idx
  on public.vacancies (user_id, created_at desc);

-- RLS увімкнено без політик: публічний (anon) ключ нічого не бачить,
-- доступ має лише secret/service_role ключ, який живе на сервері.
alter table public.vacancies enable row level security;
