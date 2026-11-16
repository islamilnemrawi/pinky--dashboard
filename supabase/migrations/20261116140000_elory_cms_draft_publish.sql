alter table public.site_customizations
  add column if not exists draft_config jsonb,
  add column if not exists draft_updated_at timestamptz;

create or replace function public.admin_save_site_customization_draft(p_config jsonb)
returns boolean language plpgsql security definer set search_path = ''
as $function$
begin
  if not public.elory_can_edit_site() then
    raise exception 'not_authorized' using errcode = '42501';
  end if;
  if p_config is null or jsonb_typeof(p_config) <> 'object' then
    raise exception 'invalid_site_config' using errcode = '22023';
  end if;
  update public.site_customizations set draft_config=p_config,draft_updated_at=now() where id=1;
  if not found then
    insert into public.site_customizations(id,config,draft_config,draft_updated_at)
    values(1,'{}'::jsonb,p_config,now());
  end if;
  return true;
end;
$function$;

create or replace function public.admin_clear_site_customization_draft()
returns boolean language plpgsql security definer set search_path = ''
as $function$
begin
  if not public.elory_can_edit_site() then
    raise exception 'not_authorized' using errcode = '42501';
  end if;
  update public.site_customizations set draft_config=null,draft_updated_at=null where id=1;
  return true;
end;
$function$;

revoke all on function public.admin_save_site_customization_draft(jsonb) from public,anon;
revoke all on function public.admin_clear_site_customization_draft() from public,anon;
grant execute on function public.admin_save_site_customization_draft(jsonb) to authenticated;
grant execute on function public.admin_clear_site_customization_draft() to authenticated;


create or replace function public.admin_get_site_customization_draft()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_draft jsonb;
begin
  if not public.elory_can_edit_site() then
    raise exception 'not_authorized' using errcode = '42501';
  end if;
  select draft_config into v_draft
  from public.site_customizations
  where id = 1;
  return v_draft;
end;
$function$;

revoke all on function public.admin_get_site_customization_draft() from public, anon;
grant execute on function public.admin_get_site_customization_draft() to authenticated;
