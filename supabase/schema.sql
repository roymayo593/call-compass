-- Run once in the Supabase SQL editor. No transcript data belongs in this database.
create table if not exists public.calls (
 id uuid primary key,
 owner_hash text not null,
 prospect text not null check (length(prospect) between 1 and 120),
 company text not null default '' check (length(company) <= 160),
 started_at timestamptz not null default now(),
 ended_at timestamptz,
 reached_stage smallint not null default 1 check (reached_stage between 1 and 8),
 outcome text check (outcome in ('meeting','callback','send_information','referral','not_interested','do_not_call','wrong_person','moved_company','disconnected','other')),
 next_step text not null default '' check (length(next_step) <= 1000),
 summary text not null default ''
);
create index if not exists calls_owner_started on public.calls(owner_hash, started_at desc);
create table if not exists public.call_stages (
 call_id uuid references public.calls(id) on delete cascade,
 stage smallint check (stage between 1 and 8),
 result text not null check (length(result) between 1 and 120),
 words text not null default '' check (length(words) <= 4000),
 updated_at timestamptz not null default now(),
 primary key(call_id, stage)
);
alter table public.calls enable row level security;
alter table public.call_stages enable row level security;
revoke all on public.calls, public.call_stages from anon, authenticated;
grant all on public.calls, public.call_stages to service_role;
-- Lock the parent row so stage updates and closing cannot race.
create or replace function public.save_call_stage(p_id uuid, p_owner text, p_stage int, p_result text, p_words text)
returns void language plpgsql set search_path = public as $$
begin
 perform 1 from calls where id=p_id and owner_hash=p_owner and ended_at is null for update;
 if not found then raise exception 'Call unavailable or closed'; end if;
 insert into call_stages(call_id,stage,result,words) values(p_id,p_stage,p_result,p_words)
 on conflict(call_id,stage) do update set result=excluded.result, words=excluded.words, updated_at=now();
 update calls set reached_stage=greatest(reached_stage,p_stage) where id=p_id;
end; $$;
create or replace function public.close_call(p_id uuid,p_owner text,p_stage int,p_outcome text,p_next text)
returns void language plpgsql set search_path = public as $$
declare c calls;
begin
 select * into c from calls where id=p_id and owner_hash=p_owner for update;
 if not found then raise exception 'Call unavailable'; end if;
 if c.ended_at is not null then return; end if;
 update calls set ended_at=now(),reached_stage=greatest(reached_stage,p_stage),outcome=p_outcome,next_step=p_next where id=p_id;
end; $$;
revoke all on function public.save_call_stage(uuid,text,int,text,text) from public,anon,authenticated;
revoke all on function public.close_call(uuid,text,int,text,text) from public,anon,authenticated;
grant execute on function public.save_call_stage(uuid,text,int,text,text) to service_role;
grant execute on function public.close_call(uuid,text,int,text,text) to service_role;
