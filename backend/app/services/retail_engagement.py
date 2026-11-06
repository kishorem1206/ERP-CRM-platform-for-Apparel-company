"""Retail Sales stage 2 — coupons, loyalty points and birthday offers.

Mixed into RetailService (it uses self.db and self.get_settings).

Loyalty points live in a ledger (retail_loyalty_ledger); the customer's
`loyalty_points` is the running balance. Points are earned on what's paid:
a cash bill at once, a credit bill once it is fully collected. They lapse
`points_expiry_days` after they're earned, oldest first: whatever was earned
before the cut-off and hasn't since been used or expired is expired.
"""
import secrets
import string
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, or_, select

from app.domain.business_rules import BusinessRulesError
from app.models.retail import RetailCoupon, RetailCouponRedemption, RetailCustomer, RetailInvoice, RetailLoyaltyEntry

CENT = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


def next_birthday(dob: date, on: date) -> date:
    """The next birthday on or after `on` (29 Feb falls on 28 Feb in other years)."""
    def in_year(y: int) -> date:
        return date(y, dob.month, min(dob.day, monthrange(y, dob.month)[1]))
    this_year = in_year(on.year)
    return this_year if this_year >= on else in_year(on.year + 1)


def coupon_state(c: RetailCoupon, used: int, on: date) -> str:
    if c.status != "active":
        return "inactive"
    if on < c.start_date:
        return "scheduled"
    if on > c.expiry_date:
        return "expired"
    if c.max_uses is not None and used >= c.max_uses:
        return "used_up"
    return "active"


class RetailEngagementMixin:
    # ── Coupons ────────────────────────────────────────────────────────────

    async def coupon_usage(self, coupon_ids: list[UUID]) -> dict[UUID, tuple[int, Decimal]]:
        if not coupon_ids:
            return {}
        rows = (await self.db.execute(
            select(RetailCouponRedemption.coupon_id, func.count(), func.coalesce(func.sum(RetailCouponRedemption.discount_amount), 0))
            .where(RetailCouponRedemption.coupon_id.in_(coupon_ids), RetailCouponRedemption.status == "active")
            .group_by(RetailCouponRedemption.coupon_id)
        )).all()
        return {cid: (n, Decimal(total)) for cid, n, total in rows}

    async def find_usable_coupon(
        self, code: str, company_id: UUID, customer: RetailCustomer | None, on: date,
    ) -> RetailCoupon:
        """The coupon for this code if it can be used on a bill now, else a
        clear reason why not. Locks the coupon row for the bill being saved."""
        coupon = (await self.db.execute(
            select(RetailCoupon).where(RetailCoupon.company_id == company_id, RetailCoupon.code == code.strip().upper())
            .with_for_update()
        )).scalar_one_or_none()
        if not coupon:
            raise BusinessRulesError("COUPON_INVALID", f"No coupon called {code.strip().upper()}.")
        used = (await self.coupon_usage([coupon.id])).get(coupon.id, (0, Decimal("0")))[0]
        state = coupon_state(coupon, used, on)
        if state == "inactive":
            raise BusinessRulesError("COUPON_INACTIVE", f"Coupon {coupon.code} is switched off.")
        if state == "scheduled":
            raise BusinessRulesError("COUPON_NOT_STARTED", f"Coupon {coupon.code} starts on {coupon.start_date:%d %b %Y}.")
        if state == "expired":
            raise BusinessRulesError("COUPON_EXPIRED", f"Coupon {coupon.code} expired on {coupon.expiry_date:%d %b %Y}.")
        if state == "used_up":
            raise BusinessRulesError("COUPON_USED_UP", f"Coupon {coupon.code} has been used the maximum number of times.")
        if coupon.customer_id and (not customer or customer.id != coupon.customer_id):
            raise BusinessRulesError("COUPON_NOT_YOURS", f"Coupon {coupon.code} belongs to another customer.")
        if coupon.per_customer_limit:
            if not customer:
                raise BusinessRulesError("CUSTOMER_REQUIRED", f"Pick the customer to use coupon {coupon.code}.")
            by_customer = (await self.db.execute(
                select(func.count()).select_from(RetailCouponRedemption).where(
                    RetailCouponRedemption.coupon_id == coupon.id, RetailCouponRedemption.customer_id == customer.id,
                    RetailCouponRedemption.status == "active",
                )
            )).scalar() or 0
            if by_customer >= coupon.per_customer_limit:
                raise BusinessRulesError("COUPON_LIMIT", f"{customer.name} has already used coupon {coupon.code}.")
        return coupon

    async def list_coupons(self, company_id: UUID, search: str | None = None, kind: str | None = None) -> list[tuple[RetailCoupon, int, Decimal]]:
        q = select(RetailCoupon).where(RetailCoupon.company_id == company_id)
        if search:
            like = f"%{search.strip()}%"
            q = q.where(or_(RetailCoupon.code.ilike(like), RetailCoupon.name.ilike(like)))
        if kind:
            q = q.where(RetailCoupon.kind == kind)
        coupons = (await self.db.execute(q.order_by(RetailCoupon.created_at.desc()).limit(500))).scalars().all()
        usage = await self.coupon_usage([c.id for c in coupons])
        return [(c, *usage.get(c.id, (0, Decimal("0")))) for c in coupons]

    async def save_coupon(self, body, company_id: UUID, user_id: UUID, coupon_id: UUID | None = None) -> RetailCoupon:
        if body.expiry_date < body.start_date:
            raise BusinessRulesError("BAD_DATES", "Expiry date can't be before the start date.")
        if body.discount_type == "percent" and body.discount_value > 100:
            raise BusinessRulesError("BAD_VALUE", "A percentage coupon can't be more than 100%.")
        clash = (await self.db.execute(
            select(RetailCoupon.id).where(RetailCoupon.company_id == company_id, RetailCoupon.code == body.code)
        )).scalar_one_or_none()
        if clash and clash != coupon_id:
            raise BusinessRulesError("DUPLICATE_CODE", f"Coupon code {body.code} is already in use.")
        data = body.model_dump()
        now = datetime.now(timezone.utc)
        if coupon_id:
            coupon = (await self.db.execute(
                select(RetailCoupon).where(RetailCoupon.id == coupon_id, RetailCoupon.company_id == company_id)
            )).scalar_one_or_none()
            if not coupon:
                raise BusinessRulesError("NOT_FOUND", "Coupon not found")
            used = (await self.coupon_usage([coupon.id])).get(coupon.id, (0, Decimal("0")))[0]
            if used and data["code"] != coupon.code:
                raise BusinessRulesError("LOCKED", "A coupon that has been used can't change its code.")
            if coupon.kind == "birthday":
                data.pop("kind")
            for k, v in data.items():
                setattr(coupon, k, v)
            coupon.updated_at = now
        else:
            coupon = RetailCoupon(company_id=company_id, created_by=user_id, created_at=now, **data)
            self.db.add(coupon)
        await self.db.flush()
        return coupon

    async def coupon_redemptions(self, coupon_id: UUID, company_id: UUID) -> list[dict]:
        rows = (await self.db.execute(
            select(RetailCouponRedemption, RetailInvoice.invoice_number, RetailInvoice.invoice_date, RetailCustomer.name)
            .join(RetailInvoice, RetailInvoice.id == RetailCouponRedemption.invoice_id)
            .outerjoin(RetailCustomer, RetailCustomer.id == RetailCouponRedemption.customer_id)
            .where(RetailCouponRedemption.coupon_id == coupon_id, RetailCouponRedemption.company_id == company_id)
            .order_by(RetailCouponRedemption.created_at.desc())
        )).all()
        return [{
            "invoice_id": r.invoice_id, "invoice_number": num, "invoice_date": d, "customer_name": name,
            "discount_amount": r.discount_amount, "status": r.status,
        } for r, num, d, name in rows]

    async def available_coupons(self, customer: RetailCustomer | None, company_id: UUID, on: date) -> list[RetailCoupon]:
        """Coupons the counter can offer: this customer's own (e.g. birthday)
        plus open ones still valid today."""
        q = select(RetailCoupon).where(
            RetailCoupon.company_id == company_id, RetailCoupon.status == "active",
            RetailCoupon.start_date <= on, RetailCoupon.expiry_date >= on,
        )
        q = q.where(or_(RetailCoupon.customer_id.is_(None), RetailCoupon.customer_id == customer.id) if customer else RetailCoupon.customer_id.is_(None))
        coupons = (await self.db.execute(q.order_by(RetailCoupon.customer_id.is_(None), RetailCoupon.expiry_date))).scalars().all()
        usage = await self.coupon_usage([c.id for c in coupons])
        out = []
        for c in coupons:
            if coupon_state(c, usage.get(c.id, (0, 0))[0], on) != "active":
                continue
            if c.per_customer_limit and customer:
                mine = (await self.db.execute(
                    select(func.count()).select_from(RetailCouponRedemption).where(
                        RetailCouponRedemption.coupon_id == c.id, RetailCouponRedemption.customer_id == customer.id,
                        RetailCouponRedemption.status == "active",
                    )
                )).scalar() or 0
                if mine >= c.per_customer_limit:
                    continue
            out.append(c)
        return out[:20]

    # ── Loyalty points ─────────────────────────────────────────────────────

    def _add_points(
        self, customer: RetailCustomer, entry_type: str, points: int, user_id: UUID | None, *,
        invoice_id: UUID | None = None, reason: str | None = None, expires_on: date | None = None,
    ) -> None:
        customer.loyalty_points = (customer.loyalty_points or 0) + points
        self.db.add(RetailLoyaltyEntry(
            company_id=customer.company_id, customer_id=customer.id, entry_type=entry_type, points=points,
            balance_after=customer.loyalty_points, invoice_id=invoice_id, reason=reason, expires_on=expires_on,
            created_by=user_id, created_at=datetime.now(timezone.utc),
        ))

    async def _award_points(self, invoice: RetailInvoice, customer: RetailCustomer, settings, user_id: UUID | None) -> None:
        kept = (invoice.points_earned or 0) - (invoice.points_returned or 0)
        if invoice.points_awarded or kept <= 0 or not settings.loyalty_enabled:
            return
        expires = date.today() + timedelta(days=settings.points_expiry_days) if settings.points_expiry_days else None
        self._add_points(customer, "earned", kept, user_id, invoice_id=invoice.id,
                         reason=f"Bill {invoice.invoice_number}", expires_on=expires)
        invoice.points_awarded = True

    async def expire_points(self, customer: RetailCustomer, on: date | None = None) -> int:
        """Expire points earned before their expiry date that haven't been
        used yet (oldest first). Returns how many expired now."""
        on = on or date.today()
        rows = (await self.db.execute(
            select(RetailLoyaltyEntry.entry_type, RetailLoyaltyEntry.points, RetailLoyaltyEntry.expires_on,
                   RetailLoyaltyEntry.invoice_id)
            .where(RetailLoyaltyEntry.customer_id == customer.id)
        )).all()
        # Points taken back from a cancelled bill were never really earned.
        taken_back = {inv for t, p, _, inv in rows if t == "reversed" and p < 0 and inv}
        lapsed = sum(
            p for t, p, exp, inv in rows
            if t in ("earned", "adjusted") and p > 0 and exp is not None and exp < on and inv not in taken_back
        )
        # Used = redeemed or removed by hand, less redemptions given back on cancelled bills.
        used = (
            -sum(p for t, p, _, _ in rows if t == "redeemed" or (t == "adjusted" and p < 0))
            - sum(p for t, p, _, _ in rows if t == "reversed" and p > 0)
        )
        already = -sum(p for t, p, _, _ in rows if t == "expired")
        due = max(0, lapsed - used) - already
        due = min(due, max(customer.loyalty_points, 0))
        if due > 0:
            self._add_points(customer, "expired", -due, None, reason="Points reached their expiry date")
            await self.db.flush()
        return max(due, 0)

    async def adjust_points(self, customer_id: UUID, points: int, reason: str, company_id: UUID, user_id: UUID) -> RetailCustomer:
        customer = (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.id == customer_id, RetailCustomer.company_id == company_id).with_for_update()
        )).scalar_one_or_none()
        if not customer:
            raise BusinessRulesError("NOT_FOUND", "Customer not found")
        if points < 0 and customer.loyalty_points + points < 0:
            raise BusinessRulesError("NOT_ENOUGH_POINTS", f"{customer.name} has only {customer.loyalty_points} points.")
        settings = await self.get_settings(company_id)
        expires = (date.today() + timedelta(days=settings.points_expiry_days)) if points > 0 and settings.points_expiry_days else None
        self._add_points(customer, "adjusted", points, user_id, reason=reason.strip(), expires_on=expires)
        await self.db.flush()
        return customer

    async def loyalty_ledger(self, customer_id: UUID, company_id: UUID) -> list[tuple[RetailLoyaltyEntry, str | None]]:
        return (await self.db.execute(
            select(RetailLoyaltyEntry, RetailInvoice.invoice_number)
            .outerjoin(RetailInvoice, RetailInvoice.id == RetailLoyaltyEntry.invoice_id)
            .where(RetailLoyaltyEntry.customer_id == customer_id, RetailLoyaltyEntry.company_id == company_id)
            .order_by(RetailLoyaltyEntry.created_at.desc())
        )).all()

    async def loyalty_summary(self, company_id: UUID) -> dict:
        settings = await self.get_settings(company_id)
        sums = dict((await self.db.execute(
            select(RetailLoyaltyEntry.entry_type, func.coalesce(func.sum(RetailLoyaltyEntry.points), 0))
            .where(RetailLoyaltyEntry.company_id == company_id).group_by(RetailLoyaltyEntry.entry_type)
        )).all())
        members = (await self.db.execute(
            select(func.count(), func.coalesce(func.sum(RetailCustomer.loyalty_points), 0))
            .where(RetailCustomer.company_id == company_id, RetailCustomer.loyalty_points > 0)
        )).one()
        top = (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.company_id == company_id, RetailCustomer.loyalty_points > 0)
            .order_by(RetailCustomer.loyalty_points.desc()).limit(10)
        )).scalars().all()
        outstanding = int(members[1] or 0)
        return {
            "enabled": settings.loyalty_enabled,
            "customers_with_points": members[0],
            "points_issued": int(sums.get("earned", 0)) + max(int(sums.get("adjusted", 0)), 0),
            "points_redeemed": -int(sums.get("redeemed", 0)),
            "points_expired": -int(sums.get("expired", 0)),
            "points_outstanding": outstanding,
            "liability": _q(Decimal(outstanding) * settings.point_value),
            "top_customers": [{"id": c.id, "name": c.name, "mobile": c.mobile, "points": c.loyalty_points} for c in top],
        }

    async def expire_all_points(self, company_id: UUID, on: date | None = None) -> int:
        customers = (await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.company_id == company_id, RetailCustomer.loyalty_points > 0)
        )).scalars().all()
        return sum([await self.expire_points(c, on) for c in customers])

    # ── Birthdays ──────────────────────────────────────────────────────────

    async def generate_birthday_coupons(self, company_id: UUID, on: date | None = None, user_id: UUID | None = None) -> int:
        """One coupon per customer per birthday, for birthdays in the next
        `birthday_lead_days` days. Safe to run any number of times."""
        on = on or date.today()
        settings = await self.get_settings(company_id)
        if not settings.birthday_enabled:
            return 0
        customers = (await self.db.execute(
            select(RetailCustomer).where(
                RetailCustomer.company_id == company_id, RetailCustomer.status == "active",
                RetailCustomer.date_of_birth.is_not(None),
            )
        )).scalars().all()
        made = 0
        for c in customers:
            bday = next_birthday(c.date_of_birth, on)
            if (bday - on).days > settings.birthday_lead_days:
                continue
            exists = (await self.db.execute(
                select(RetailCoupon.id).where(
                    RetailCoupon.customer_id == c.id, RetailCoupon.kind == "birthday", RetailCoupon.birthday_year == bday.year,
                )
            )).scalar_one_or_none()
            if exists:
                continue
            if settings.birthday_window == "month":
                start, end = bday.replace(day=1), bday.replace(day=monthrange(bday.year, bday.month)[1])
            else:
                start, end = bday - timedelta(days=3), bday + timedelta(days=3)
            start = max(start, on)
            code = await self._unique_code("BDAY-", company_id)
            self.db.add(RetailCoupon(
                company_id=company_id, code=code, name=f"Birthday offer — {c.name}",
                description=f"Birthday {bday:%d %b %Y}", kind="birthday",
                discount_type=settings.birthday_discount_type, discount_value=settings.birthday_discount_value,
                min_purchase=settings.birthday_min_purchase, max_discount=settings.birthday_max_discount,
                start_date=start, expiry_date=end, max_uses=1, per_customer_limit=1,
                product_ids=[], category_ids=[], customer_id=c.id, birthday_year=bday.year, status="active",
                created_by=user_id, created_at=datetime.now(timezone.utc),
            ))
            made += 1
        await self.db.flush()
        return made

    async def _unique_code(self, prefix: str, company_id: UUID) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = prefix + "".join(secrets.choice(alphabet) for _ in range(6))
            taken = (await self.db.execute(
                select(RetailCoupon.id).where(RetailCoupon.company_id == company_id, RetailCoupon.code == code)
            )).scalar_one_or_none()
            if not taken:
                return code
        raise BusinessRulesError("CODE_CLASH", "Could not make a unique coupon code — try again.")

    async def birthday_dashboard(self, company_id: UUID, on: date | None = None) -> dict:
        on = on or date.today()
        customers = (await self.db.execute(
            select(RetailCustomer).where(
                RetailCustomer.company_id == company_id, RetailCustomer.status == "active",
                RetailCustomer.date_of_birth.is_not(None),
            )
        )).scalars().all()
        coupons = (await self.db.execute(
            select(RetailCoupon).where(RetailCoupon.company_id == company_id, RetailCoupon.kind == "birthday")
        )).scalars().all()
        usage = await self.coupon_usage([c.id for c in coupons])
        by_customer = {(c.customer_id, c.birthday_year): c for c in coupons}

        def row(c: RetailCustomer) -> dict:
            bday = next_birthday(c.date_of_birth, on)
            coupon = by_customer.get((c.id, bday.year))
            return {
                "customer_id": c.id, "name": c.name, "mobile": c.mobile, "birthday": bday,
                "days_away": (bday - on).days, "age": bday.year - c.date_of_birth.year,
                "coupon_code": coupon.code if coupon else None,
                "coupon_used": bool(coupon and usage.get(coupon.id, (0, 0))[0]),
            }
        upcoming = sorted((row(c) for c in customers), key=lambda r: r["days_away"])
        this_year = [c for c in coupons if c.birthday_year == on.year]
        redeemed = sum(1 for c in this_year if usage.get(c.id, (0, 0))[0])
        return {
            "today": [r for r in upcoming if r["days_away"] == 0],
            "next_7": [r for r in upcoming if 0 < r["days_away"] <= 7],
            "next_30": [r for r in upcoming if 7 < r["days_away"] <= 30],
            "coupons_generated": len(this_year),
            "coupons_redeemed": redeemed,
            "redemption_pct": round(redeemed * 100 / len(this_year), 1) if this_year else 0,
        }
