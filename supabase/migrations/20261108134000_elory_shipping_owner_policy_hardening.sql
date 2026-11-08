create or replace function public.admin_save_shipping_governorate(
  p_governorate text,
  p_price numeric,
  p_active boolean default true,
  p_centers_enabled boolean default true
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  r public.shipping_governorates%rowtype;
  v_previous_price numeric;
  v_updated_centers integer := 0;
begin
  if not public.has_staff_permission('shipping.manage') then
    raise exception 'ليس لديك صلاحية إدارة الشحن';
  end if;

  if nullif(trim(p_governorate), '') is null
     or p_price is null
     or p_price < 0 then
    raise exception 'بيانات سعر الشحن غير صحيحة';
  end if;

  select price
    into v_previous_price
    from public.shipping_governorates
   where governorate = trim(p_governorate);

  insert into public.shipping_governorates(
    governorate, price, active, centers_enabled, updated_at
  )
  values(
    trim(p_governorate), p_price,
    coalesce(p_active, true),
    coalesce(p_centers_enabled, true),
    now()
  )
  on conflict(governorate)
  do update set
    price = excluded.price,
    active = excluded.active,
    centers_enabled = excluded.centers_enabled,
    updated_at = now()
  returning * into r;

  -- A changed governorate base price must reach existing centers too.
  -- Preserve center-specific rates when only active/settings flags change.
  if v_previous_price is distinct from p_price then
    update public.shipping_centers
       set price = p_price
     where governorate = trim(p_governorate);
    get diagnostics v_updated_centers = row_count;
  end if;

  return jsonb_build_object(
    'governorate', r.governorate,
    'price', r.price,
    'active', r.active,
    'centers_enabled', r.centers_enabled,
    'updated_centers', v_updated_centers
  );
end;
$function$;

revoke all on function public.admin_save_shipping_governorate(text, numeric, boolean, boolean) from public, anon;
grant execute on function public.admin_save_shipping_governorate(text, numeric, boolean, boolean) to authenticated;

-- Remove legacy broad policies that bypass the permission-specific rules.
drop policy if exists "Authenticated can manage products" on public.products;
drop policy if exists "staff can manage products" on public.products;

drop policy if exists "pinky_orders_staff_manage" on public.orders;
drop policy if exists "staff can read orders" on public.orders;
drop policy if exists "staff can update orders" on public.orders;
drop policy if exists "elora_staff_read_orders" on public.orders;

drop policy if exists "staff can manage shipping" on public.shipping_centers;
drop policy if exists "Staff shipping center select permission" on public.shipping_centers;
drop policy if exists "Staff shipping center manage permission" on public.shipping_centers;

create policy "Staff shipping center select permission"
on public.shipping_centers
for select
to authenticated
using (public.has_staff_permission('shipping.manage'));

create policy "Staff shipping center manage permission"
on public.shipping_centers
for all
to authenticated
using (public.has_staff_permission('shipping.manage'))
with check (public.has_staff_permission('shipping.manage'));
