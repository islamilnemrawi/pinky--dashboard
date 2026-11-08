create or replace function public.elory_snapshot_order_item_costs()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_items jsonb;
begin
  if new.items is null or jsonb_typeof(new.items) <> 'array' then
    return new;
  end if;

  select coalesce(
    jsonb_agg(
      x.item || jsonb_build_object(
        'product_name',
          coalesce(nullif(x.item->>'product_name', ''),
                   nullif(x.item->>'name', ''),
                   p.name),
        'product_image',
          coalesce(nullif(x.item->>'product_image', ''),
                   nullif(x.item->>'image', ''),
                   p.image),
        'product_code',
          coalesce(nullif(x.item->>'product_code', ''),
                   nullif(x.item->>'code', ''),
                   p.code,
                   p.sku),
        'wholesale_price',
          case
            when coalesce(x.item->>'wholesale_price', '') ~ '^-?[0-9]+(\.[0-9]+)?$'
              then (x.item->>'wholesale_price')::numeric
            else p.wholesale_price
          end
      )
      order by x.ordinality
    ),
    '[]'::jsonb
  )
  into v_items
  from jsonb_array_elements(new.items) with ordinality as x(item, ordinality)
  left join public.products p
    on p.id::text = coalesce(x.item->>'product_id', x.item->>'id');

  new.items := v_items;
  return new;
end;
$function$;

drop trigger if exists elory_snapshot_order_item_costs on public.orders;
create trigger elory_snapshot_order_item_costs
before insert or update of items on public.orders
for each row
execute function public.elory_snapshot_order_item_costs();

revoke all on function public.elory_snapshot_order_item_costs() from public, anon, authenticated;

create or replace function public.get_customer_orders(
  p_access_token text default null,
  p_phone text default null
)
returns table(
  id uuid,
  order_number text,
  user_id uuid,
  created_at timestamptz,
  status text,
  items jsonb,
  shipping_cost numeric,
  total numeric,
  governorate text,
  center text
)
language sql
stable
security definer
set search_path = ''
as $function$
  select
    o.id,
    coalesce(to_jsonb(o)->>'order_number', to_jsonb(o)->>'order_code', o.id::text) as order_number,
    o.user_id,
    o.created_at,
    o.status,
    case
      when jsonb_typeof(o.items) = 'array' then
        coalesce((
          select jsonb_agg(
            x.item
              - 'wholesale_price'
              - 'product_code'
              - 'product_image'
              - 'product_name'
              - 'wholesalePrice'
              - 'productCode'
              - 'productImage'
              - 'productName'
            order by x.ordinality
          )
          from jsonb_array_elements(o.items) with ordinality as x(item, ordinality)
        ), '[]'::jsonb)
      else coalesce(o.items, '[]'::jsonb)
    end as items,
    coalesce(o.shipping_cost, 0) as shipping_cost,
    coalesce(o.total, 0) as total,
    o.governorate,
    o.center
  from public.orders o
  where (
    (auth.uid() is not null and o.user_id = auth.uid())
    or (
      p_access_token is not null
      and length(trim(p_access_token)) >= 24
      and o.customer_access_token = trim(p_access_token)
    )
  )
  order by o.created_at desc;
$function$;
