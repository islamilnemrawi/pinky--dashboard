-- Elory coupon repair:
-- 1) Preserve the first-order-only choice from the dashboard.
-- 2) Use permissive staff policies correctly (the previous restrictive-only
--    INSERT/UPDATE/DELETE policies could never authorize a write by themselves).
-- 3) Enforce first-order-only on the server before any order is inserted or changed.

ALTER TABLE public.coupons
  ADD COLUMN IF NOT EXISTS first_order_only boolean NOT NULL DEFAULT false;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.coupons'::regclass
      AND conname = 'coupons_percent_discount_max_100_check'
  ) THEN
    ALTER TABLE public.coupons
      ADD CONSTRAINT coupons_percent_discount_max_100_check
      CHECK (discount_type <> 'percent' OR discount_value <= 100);
  END IF;
END;
$$;

DROP POLICY IF EXISTS "Staff coupon delete permission" ON public.coupons;
DROP POLICY IF EXISTS "Staff coupon insert permission" ON public.coupons;
DROP POLICY IF EXISTS "Staff coupon select permission" ON public.coupons;
DROP POLICY IF EXISTS "Staff coupon update permission" ON public.coupons;

CREATE POLICY "Staff coupon delete permission"
  ON public.coupons AS PERMISSIVE FOR DELETE TO authenticated
  USING (public.has_staff_permission('coupons.manage'));

CREATE POLICY "Staff coupon insert permission"
  ON public.coupons AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (public.has_staff_permission('coupons.manage'));

CREATE POLICY "Staff coupon select permission"
  ON public.coupons AS PERMISSIVE FOR SELECT TO authenticated
  USING (public.has_staff_permission('coupons.manage'));

CREATE POLICY "Staff coupon update permission"
  ON public.coupons AS PERMISSIVE FOR UPDATE TO authenticated
  USING (public.has_staff_permission('coupons.manage'))
  WITH CHECK (public.has_staff_permission('coupons.manage'));

-- Normalize common Egyptian phone formats (010..., +20 10..., 0020 10...).
CREATE OR REPLACE FUNCTION private.elory_normalize_phone(p_phone text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = ''
AS $function$
  WITH digits AS (
    SELECT regexp_replace(coalesce(p_phone, ''), '[^0-9]', '', 'g') AS value
  )
  SELECT CASE
    WHEN value LIKE '0020%' THEN '0' || substr(value, 5)
    WHEN value LIKE '20%' AND length(value) >= 12 THEN '0' || substr(value, 3)
    WHEN length(value) = 10 AND value LIKE '1%' THEN '0' || value
    ELSE value
  END
  FROM digits;
$function$;
REVOKE ALL ON FUNCTION private.elory_normalize_phone(text) FROM PUBLIC, anon, authenticated;

-- Lock by account and normalized phone so two simultaneous checkouts cannot
-- both claim to be the customer's first purchase.
CREATE OR REPLACE FUNCTION public.elory_enforce_first_order_coupon()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  v_first_order_only boolean := false;
  v_phone text;
  v_has_previous_order boolean := false;
BEGIN
  IF nullif(trim(coalesce(NEW.coupon_code, '')), '') IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT coalesce(c.first_order_only, false)
    INTO v_first_order_only
    FROM public.coupons AS c
   WHERE upper(c.code) = upper(trim(NEW.coupon_code))
   LIMIT 1
   FOR SHARE;

  IF NOT FOUND OR v_first_order_only IS NOT TRUE THEN
    RETURN NEW;
  END IF;

  v_phone := private.elory_normalize_phone(NEW.phone);
  IF length(v_phone) < 8 THEN
    RAISE EXCEPTION 'أدخل رقم هاتف صحيحًا للتحقق من أن الكوبون مخصص لأول طلب فقط';
  END IF;

  IF NEW.user_id IS NOT NULL THEN
    PERFORM pg_advisory_xact_lock(76021001, hashtext('user:' || NEW.user_id::text));
  END IF;
  PERFORM pg_advisory_xact_lock(76021002, hashtext('phone:' || v_phone));

  SELECT EXISTS (
    SELECT 1
      FROM public.orders AS o
     WHERE o.id IS DISTINCT FROM NEW.id
       AND (
         (NEW.user_id IS NOT NULL AND o.user_id = NEW.user_id)
         OR private.elory_normalize_phone(o.phone) = v_phone
       )
       AND lower(trim(coalesce(o.status, ''))) NOT IN (
         'cancelled', 'canceled', 'failed', 'payment_failed', 'rejected',
         'ملغي', 'ملغى', 'فشل الدفع', 'فشل إنشاء الدفع'
       )
  ) INTO v_has_previous_order;

  IF v_has_previous_order THEN
    RAISE EXCEPTION 'هذا الكوبون متاح لأول طلب فقط، ورقم الهاتف أو الحساب له طلب سابق';
  END IF;

  RETURN NEW;
END;
$function$;

REVOKE ALL ON FUNCTION public.elory_enforce_first_order_coupon() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.elory_enforce_first_order_coupon() TO anon, authenticated;

DROP TRIGGER IF EXISTS elory_enforce_first_order_coupon ON public.orders;
CREATE TRIGGER elory_enforce_first_order_coupon
  BEFORE INSERT OR UPDATE OF coupon_code, phone, user_id
  ON public.orders
  FOR EACH ROW
  EXECUTE FUNCTION public.elory_enforce_first_order_coupon();

-- Preserve two-argument callers with a defaulted phone argument. The trigger
-- remains authoritative even for older cached storefront versions.
DROP FUNCTION IF EXISTS public.validate_coupon(text, numeric);

CREATE FUNCTION public.validate_coupon(
  p_code text,
  p_subtotal numeric,
  p_phone text DEFAULT NULL
)
RETURNS TABLE(
  valid boolean,
  id uuid,
  code text,
  discount_type text,
  discount_value numeric,
  max_discount numeric,
  free_shipping boolean,
  message text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  c public.coupons%rowtype;
  v_phone text;
BEGIN
  SELECT *
    INTO c
    FROM public.coupons AS coupon
   WHERE upper(coupon.code) = upper(trim(coalesce(p_code, '')))
   LIMIT 1;

  IF NOT FOUND THEN
    RETURN QUERY SELECT false, NULL::uuid, NULL::text, NULL::text,
      NULL::numeric, NULL::numeric, false, 'كود الخصم غير صحيح';
    RETURN;
  END IF;

  IF c.active IS NOT TRUE THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'كود الخصم غير مفعّل';
    RETURN;
  END IF;

  IF c.starts_at IS NOT NULL AND now() < c.starts_at THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'الكود لم يبدأ بعد';
    RETURN;
  END IF;

  IF c.expires_at IS NOT NULL AND now() > c.expires_at THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'كود الخصم منتهي';
    RETURN;
  END IF;

  IF c.usage_limit IS NOT NULL AND c.used_count >= c.usage_limit THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'تم الوصول للحد الأقصى لاستخدام الكود';
    RETURN;
  END IF;

  IF coalesce(p_subtotal, 0) < c.min_order THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'قيمة الطلب أقل من الحد الأدنى للكود';
    RETURN;
  END IF;

  IF c.discount_value <= 0 AND c.free_shipping IS NOT TRUE THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'الكود لا يحتوي على خصم أو شحن مجاني';
    RETURN;
  END IF;

  IF c.first_order_only IS TRUE AND nullif(trim(coalesce(p_phone, '')), '') IS NULL THEN
    RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
      c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'اكتب رقم الهاتف أولاً للتحقق من أن الكوبون لأول طلب فقط';
    RETURN;
  END IF;

  IF c.first_order_only IS TRUE THEN
    v_phone := private.elory_normalize_phone(p_phone);
    IF length(v_phone) < 8 THEN
      RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
        c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'أدخل رقم هاتف صحيحًا للتحقق من الكوبون';
      RETURN;
    END IF;

    IF EXISTS (
      SELECT 1
        FROM public.orders AS o
       WHERE (
           private.elory_normalize_phone(o.phone) = v_phone
           OR (auth.uid() IS NOT NULL AND o.user_id = auth.uid())
         )
         AND lower(trim(coalesce(o.status, ''))) NOT IN (
           'cancelled', 'canceled', 'failed', 'payment_failed', 'rejected',
           'ملغي', 'ملغى', 'فشل الدفع', 'فشل إنشاء الدفع'
         )
    ) THEN
      RETURN QUERY SELECT false, c.id, c.code, c.discount_type,
        c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'هذا الكوبون متاح لأول طلب فقط';
      RETURN;
    END IF;
  END IF;

  RETURN QUERY SELECT true, c.id, c.code, c.discount_type,
    c.discount_value, c.max_discount, coalesce(c.free_shipping, false), 'تم تطبيق كود الخصم';
END;
$function$;

REVOKE ALL ON FUNCTION public.validate_coupon(text, numeric, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.validate_coupon(text, numeric, text) TO anon, authenticated;

-- Check again when the order is redeemed; do not increment usage twice.
CREATE OR REPLACE FUNCTION public.redeem_coupon(
  p_coupon_id uuid,
  p_order_id uuid DEFAULT NULL::uuid,
  p_access_token text DEFAULT NULL::text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  v_order public.orders%rowtype;
  v_coupon public.coupons%rowtype;
  v_authorized boolean := false;
  v_phone text;
BEGIN
  IF p_coupon_id IS NULL OR p_order_id IS NULL THEN
    RETURN false;
  END IF;

  SELECT *
    INTO v_order
    FROM public.orders
   WHERE id = p_order_id
   FOR UPDATE;

  IF NOT FOUND
     OR v_order.coupon_redeemed_at IS NOT NULL
     OR nullif(trim(coalesce(v_order.coupon_code, '')), '') IS NULL
     OR coalesce(v_order.status, '') IN ('ملغي', 'ملغى', 'CANCELLED', 'CANCELED') THEN
    RETURN false;
  END IF;

  IF auth.role() <> 'service_role' THEN
    v_authorized := (
      auth.uid() IS NOT NULL
      AND v_order.user_id = auth.uid()
    ) OR (
      p_access_token IS NOT NULL
      AND length(trim(p_access_token)) >= 24
      AND v_order.customer_access_token = p_access_token
    );
    IF NOT v_authorized THEN
      RETURN false;
    END IF;
  END IF;

  SELECT *
    INTO v_coupon
    FROM public.coupons
   WHERE id = p_coupon_id
   FOR UPDATE;

  IF NOT FOUND
     OR v_coupon.active IS NOT TRUE
     OR NOT (
       upper(trim(v_order.coupon_code)) = upper(trim(v_coupon.code))
       OR trim(v_order.coupon_code) = v_coupon.id::text
     )
     OR (v_coupon.starts_at IS NOT NULL AND now() < v_coupon.starts_at)
     OR (v_coupon.expires_at IS NOT NULL AND now() > v_coupon.expires_at)
     OR (v_coupon.usage_limit IS NOT NULL AND v_coupon.used_count >= v_coupon.usage_limit) THEN
    RETURN false;
  END IF;

  IF v_coupon.first_order_only IS TRUE THEN
    v_phone := private.elory_normalize_phone(v_order.phone);
    IF v_order.user_id IS NOT NULL THEN
      PERFORM pg_advisory_xact_lock(76021001, hashtext('user:' || v_order.user_id::text));
    END IF;
    PERFORM pg_advisory_xact_lock(76021002, hashtext('phone:' || v_phone));

    IF EXISTS (
      SELECT 1
        FROM public.orders AS o
       WHERE o.id <> v_order.id
         AND (
           (v_order.user_id IS NOT NULL AND o.user_id = v_order.user_id)
           OR private.elory_normalize_phone(o.phone) = v_phone
         )
         AND lower(trim(coalesce(o.status, ''))) NOT IN (
           'cancelled', 'canceled', 'failed', 'payment_failed', 'rejected',
           'ملغي', 'ملغى', 'فشل الدفع', 'فشل إنشاء الدفع'
         )
    ) THEN
      RETURN false;
    END IF;
  END IF;

  UPDATE public.coupons
     SET used_count = used_count + 1
   WHERE id = p_coupon_id
     AND active IS TRUE
     AND (usage_limit IS NULL OR used_count < usage_limit);

  IF NOT FOUND THEN
    RETURN false;
  END IF;

  UPDATE public.orders
     SET coupon_redeemed_at = now()
   WHERE id = p_order_id
     AND coupon_redeemed_at IS NULL;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'تعذر تسجيل استخدام الكوبون للطلب';
  END IF;

  RETURN true;
END;
$function$;

REVOKE ALL ON FUNCTION public.redeem_coupon(uuid, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.redeem_coupon(uuid, uuid, text) TO anon, authenticated;

-- Keep a rollback copy of the existing slides in supabase/backups before clearing.
UPDATE public.site_customizations
   SET config = jsonb_set(config, '{hero,slides}', '[]'::jsonb, true),
       updated_at = now()
 WHERE id = 1
   AND jsonb_typeof(config -> 'hero' -> 'slides') = 'array';

NOTIFY pgrst, 'reload schema';
