create or replace function public.has_staff_permission(p_permission text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $function$
declare
  v_uid uuid := auth.uid();
  v_email text;
  v_role text;
  v_permissions jsonb;
  v_active boolean;
  v_storage_key text;
  v_alias_key text;
begin
  if v_uid is null then
    return false;
  end if;

  select lower(coalesce(email, ''))
    into v_email
    from auth.users
   where id = v_uid;

  select role, permissions, active
    into v_role, v_permissions, v_active
    from public.staff_profiles
   where id = v_uid
   limit 1;

  if v_email = 'ilnemrawi@gmail.com' then
    return coalesce(v_active, true);
  end if;

  if coalesce(v_active, false) is not true then
    return false;
  end if;

  if lower(coalesce(v_role, '')) in ('owner', 'admin', 'manager') then
    return true;
  end if;

  v_alias_key := lower(trim(coalesce(p_permission, '')));
  v_storage_key := case v_alias_key
    when 'orders.view' then 'MANAGE_ORDERS'
    when 'orders.edit' then 'UPDATE_ORDER_STATUS'
    when 'orders.delete' then 'MANAGE_ORDERS'
    when 'products.view' then 'MANAGE_PRODUCTS'
    when 'products.add' then 'MANAGE_PRODUCTS'
    when 'products.edit' then 'MANAGE_PRODUCTS'
    when 'products.delete' then 'MANAGE_PRODUCTS'
    when 'products.manage' then 'MANAGE_PRODUCTS'
    when 'products.wholesale_prices' then 'VIEW_WHOLESALE_PRICES'
    when 'products.internal_codes' then 'VIEW_INTERNAL_CODES'
    when 'categories.manage' then 'MANAGE_CATEGORIES'
    when 'offers.manage' then 'MANAGE_OFFERS'
    when 'coupons.manage' then 'MANAGE_COUPONS'
    when 'customers.manage' then 'MANAGE_CUSTOMERS'
    when 'prime.manage' then 'MANAGE_PRIME'
    when 'shipping.manage' then 'MANAGE_SHIPPING'
    when 'payments.manage' then 'MANAGE_PAYMENT_METHODS'
    when 'staff.manage' then 'MANAGE_STAFF'
    when 'website.manage' then 'MANAGE_WEBSITE_EDITOR'
    when 'site.edit' then 'MANAGE_WEBSITE_EDITOR'
    when 'analytics.view' then 'VIEW_ANALYTICS'
    when 'analytics.profit' then 'VIEW_PROFIT'
    when 'notifications.view' then 'VIEW_NOTIFICATIONS'
    when 'settings.manage' then 'MANAGE_SETTINGS'
    when 'store.manage' then 'MANAGE_SETTINGS'
    when 'dashboard.view' then 'VIEW_DASHBOARD'
    else upper(replace(v_alias_key, '.', '_'))
  end;

  if coalesce((v_permissions ->> p_permission)::boolean, false)
     or coalesce((v_permissions ->> v_storage_key)::boolean, false) then
    return true;
  end if;

  if v_alias_key = 'orders.edit'
     and coalesce((v_permissions ->> 'MANAGE_ORDERS')::boolean, false) then
    return true;
  end if;

  return false;
exception
  when invalid_text_representation then
    return false;
end;
$function$;

create or replace function public.is_elora_staff()
returns boolean
language sql
stable
security definer
set search_path = ''
as $function$
  select exists (
    select 1
      from public.staff_profiles
     where id = auth.uid()
       and active = true
  );
$function$;

create or replace function public.admin_grant_prime_by_email(
  p_email text,
  p_days integer default 30
)
returns table(success boolean, user_id uuid, expires_at timestamptz, message text)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  target_id uuid;
  current_expiry timestamptz;
  new_expiry timestamptz;
begin
  if not public.has_staff_permission('prime.manage') then
    return query select false, null::uuid, null::timestamptz, 'ليس لديك صلاحية تفعيل Prime يدويًا'::text;
    return;
  end if;

  if nullif(trim(p_email), '') is null or coalesce(p_days, 0) < 1 then
    return query select false, null::uuid, null::timestamptz, 'البريد أو عدد الأيام غير صحيح'::text;
    return;
  end if;

  select id
    into target_id
    from auth.users
   where lower(email) = lower(trim(p_email))
   limit 1;

  if target_id is null then
    return query select false, null::uuid, null::timestamptz, 'البريد غير مسجل في حسابات Elora'::text;
    return;
  end if;

  select max(ps.expires_at)
    into current_expiry
    from public.prime_subscriptions ps
   where ps.user_id = target_id
     and ps.active = true
     and ps.expires_at > now();

  new_expiry := greatest(coalesce(current_expiry, now()), now())
                + make_interval(days => p_days);

  update public.prime_subscriptions
     set active = false
   where user_id = target_id
     and active = true;

  insert into public.prime_subscriptions(user_id, started_at, expires_at, active)
  values(target_id, now(), new_expiry, true);

  return query select true, target_id, new_expiry, 'تم تفعيل Elora Prime بنجاح'::text;
end;
$function$;

revoke all on function public.has_staff_permission(text) from public, anon;
grant execute on function public.has_staff_permission(text) to authenticated;
revoke all on function public.is_elora_staff() from public, anon;
grant execute on function public.is_elora_staff() to authenticated;
revoke all on function public.elora_admin_allowed() from public, anon;
grant execute on function public.elora_admin_allowed() to authenticated;
revoke all on function public.get_my_prime_status() from public, anon;
grant execute on function public.get_my_prime_status() to authenticated;
revoke all on function public.register_dashboard_push_device(text, text) from public, anon;
grant execute on function public.register_dashboard_push_device(text, text) to authenticated;

do $$
declare
  f record;
begin
  for f in
    select n.nspname,
           p.proname,
           coalesce((
             select string_agg(format_type(arg_type, null), ', ' order by ordinality)
               from unnest(p.proargtypes) with ordinality as a(arg_type, ordinality)
           ), '') as arg_types
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname like 'admin_%'
       and p.prosecdef
  loop
    execute format('revoke all on function %I.%I(%s) from public, anon', f.nspname, f.proname, f.arg_types);
    execute format('grant execute on function %I.%I(%s) to authenticated', f.nspname, f.proname, f.arg_types);
  end loop;
end;
$$;

revoke all on function public.activate_prime_from_paid_order() from public, anon, authenticated;
revoke all on function public.elora_assign_order_number() from public, anon, authenticated;
revoke all on function public.elora_link_order_to_customer() from public, anon, authenticated;
revoke all on function public.prepare_pinky_order_identity() from public, anon, authenticated;
revoke all on function public.rls_auto_enable() from public, anon, authenticated;
grant execute on function public.rls_auto_enable() to service_role;

alter function public.elora_protect_order_number() set search_path = '';

drop policy if exists "staff can manage banners" on public.banners;
create policy "Staff can manage banners permission"
on public.banners for all to authenticated
using (public.has_staff_permission('offers.manage') or public.has_staff_permission('website.manage'))
with check (public.has_staff_permission('offers.manage') or public.has_staff_permission('website.manage'));

drop policy if exists "staff can manage categories" on public.categories;
create policy "Staff can manage categories permission"
on public.categories for all to authenticated
using (public.has_staff_permission('categories.manage'))
with check (public.has_staff_permission('categories.manage'));

drop policy if exists "staff can manage offers" on public.offers;
create policy "Staff can manage offers permission"
on public.offers for all to authenticated
using (public.has_staff_permission('offers.manage'))
with check (public.has_staff_permission('offers.manage'));

drop policy if exists "pinky_prime_customer_select" on public.prime_subscriptions;
drop policy if exists "pinky_prime_staff_manage" on public.prime_subscriptions;
drop policy if exists "staff can manage prime subscriptions" on public.prime_subscriptions;
create policy "Customers or authorized staff can read prime subscriptions"
on public.prime_subscriptions for select to authenticated
using (auth.uid() = user_id or public.has_staff_permission('prime.manage'));
create policy "Staff can manage prime subscriptions permission"
on public.prime_subscriptions for all to authenticated
using (public.has_staff_permission('prime.manage'))
with check (public.has_staff_permission('prime.manage'));

drop policy if exists "staff can manage store settings" on public.store_settings;
create policy "Staff can manage store settings permission"
on public.store_settings for all to authenticated
using (public.has_staff_permission('settings.manage') or public.has_staff_permission('website.manage'))
with check (public.has_staff_permission('settings.manage') or public.has_staff_permission('website.manage'));
