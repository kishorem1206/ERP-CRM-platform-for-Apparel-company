"""ProductionService: lots, stages, MIS, stage entries, FG output."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production import (
    MaterialIssue, MaterialIssueItem,
    ProductionLot, ProductionLotSize, ProductionOutput,
    ProductionStage, ProductionStageEntry, Style,
)
from app.schemas.inventory import IssueParams, ReceiveParams
from app.schemas.production import (
    MaterialIssueCreate, MISItemCreate,
    ProductionLotCreate, ProductionLotUpdate,
    ProductionOutputCreate,
    StageCreate, StageEntryCreate, StyleCreate,
)
from app.services.inventory import InventoryService


async def _next_seq(db: AsyncSession, prefix: str, company_id: UUID, model_cls) -> str:
    """Non-safe fallback used only for MIS/OUT sequences until document_sequences covers them."""
    result = await db.execute(select(func.count()).where(model_cls.company_id == company_id))
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:05d}"


class ProductionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    async def _next_lot_number(self, company_id: UUID) -> str:
        """Concurrency-safe lot number from document_sequences (SELECT FOR UPDATE)."""
        result = await self.db.execute(
            text("""
                SELECT prefix, separator, year_format, next_number, padding
                FROM document_sequences
                WHERE company_id = :cid AND document_type = 'production_lot'
                FOR UPDATE
            """),
            {"cid": str(company_id)},
        )
        row = result.mappings().first()
        if row is None:
            # Fallback if sequence row is missing
            count = (await self.db.execute(
                select(func.count()).where(ProductionLot.company_id == company_id)
            )).scalar() or 0
            return f"LOT{count + 1:05d}"

        prefix = row["prefix"] or "LOT"
        sep = row["separator"] or ""
        next_num = row["next_number"]
        padding = row["padding"] or 5
        year_format = row["year_format"] or ""

        year_part = ""
        if year_format:
            _fmt = {"YY": "%y", "YYYY": "%Y"}.get(year_format, year_format)
            year_part = datetime.now(timezone.utc).strftime(_fmt) + sep

        lot_number = f"{prefix}{sep}{year_part}{str(next_num).zfill(padding)}"

        await self.db.execute(
            text("""
                UPDATE document_sequences SET next_number = next_number + 1
                WHERE company_id = :cid AND document_type = 'production_lot'
            """),
            {"cid": str(company_id)},
        )
        return lot_number

    # ── Styles ─────────────────────────────────────────────────────────────

    async def list_styles(self, company_id: UUID) -> list[Style]:
        result = await self.db.execute(
            select(Style).where(Style.company_id == company_id).order_by(Style.name)
        )
        return result.scalars().all()

    async def create_style(self, body: StyleCreate, company_id: UUID) -> Style:
        now = datetime.now(timezone.utc)
        s = Style(company_id=company_id, created_at=now, **body.model_dump())
        self.db.add(s)
        await self.db.flush()
        return s

    # ── Production Lots ────────────────────────────────────────────────────

    async def list_lots(
        self, company_id: UUID, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[ProductionLot], int]:
        q = (
            select(ProductionLot)
            .where(ProductionLot.company_id == company_id)
            .options(selectinload(ProductionLot.style), selectinload(ProductionLot.sizes))
        )
        if status:
            q = q.where(ProductionLot.status == status)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(ProductionLot.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_lot(self, lot_id: UUID, company_id: UUID) -> ProductionLot | None:
        result = await self.db.execute(
            select(ProductionLot)
            .where(ProductionLot.id == lot_id, ProductionLot.company_id == company_id)
            .options(
                selectinload(ProductionLot.style),
                selectinload(ProductionLot.sizes),
                selectinload(ProductionLot.stages).selectinload(ProductionStage.entries),
            )
        )
        return result.scalar_one_or_none()

    async def create_lot(self, body: ProductionLotCreate, company_id: UUID, user_id: UUID) -> ProductionLot:
        now = datetime.now(timezone.utc)
        lot_number = (body.lot_number or "").strip() or await self._next_lot_number(company_id)

        lot = ProductionLot(
            company_id=company_id, lot_number=lot_number,
            style_id=body.style_id, customer_id=body.customer_id,
            sales_order_id=body.sales_order_id, order_ref=body.order_ref,
            planned_qty=body.planned_qty, delivery_date=body.delivery_date,
            season=body.season, target_sp=body.target_sp, notes=body.notes,
            created_by=user_id, created_at=now, updated_at=now,
        )
        self.db.add(lot)
        await self.db.flush()

        for sz in body.sizes:
            self.db.add(ProductionLotSize(
                production_lot_id=lot.id, size_id=sz.size_id, planned_qty=sz.planned_qty,
            ))

        # Auto-create default stages in order
        default_stages = [
            ("cutting", "Cutting"), ("making", "Making"),
            ("finishing", "Finishing"), ("qc", "QC / Checking"),
            ("packing", "Packing"),
        ]
        for stype, sname in default_stages:
            self.db.add(ProductionStage(
                production_lot_id=lot.id, stage_type=stype, stage_name=sname,
                planned_qty=body.planned_qty, created_at=now, updated_at=now,
            ))

        await self.db.flush()
        result = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == lot.id)
            .options(selectinload(ProductionLot.style), selectinload(ProductionLot.sizes),
                     selectinload(ProductionLot.stages))
        )
        return result.scalar_one()

    async def update_lot(self, lot_id: UUID, body: ProductionLotUpdate, company_id: UUID) -> ProductionLot | None:
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        for f, v in body.model_dump(exclude_unset=True).items():
            setattr(lot, f, v)
        lot.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return lot

    async def advance_lot_status(self, lot_id: UUID, company_id: UUID, new_status: str) -> ProductionLot | None:
        valid_flow = {
            "draft": "planned", "planned": "approved",
            "approved": "in_production", "in_production": "qc",
            "qc": "packing", "packing": "ready_to_dispatch",
        }
        lot = await self.get_lot(lot_id, company_id)
        if not lot:
            return None
        if new_status not in valid_flow.values() and new_status not in ("cancelled", "completed"):
            return None
        lot.status = new_status
        lot.updated_at = datetime.now(timezone.utc)
        if new_status == "completed":
            lot.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return lot

    # ── Stages ─────────────────────────────────────────────────────────────

    async def add_stage(self, lot_id: UUID, body: StageCreate, company_id: UUID) -> ProductionStage:
        now = datetime.now(timezone.utc)
        stage = ProductionStage(
            production_lot_id=lot_id, stage_type=body.stage_type, stage_name=body.stage_name,
            planned_qty=body.planned_qty, vendor_id=body.vendor_id,
            rate_per_pc=body.rate_per_pc, notes=body.notes,
            created_at=now, updated_at=now,
        )
        self.db.add(stage)
        await self.db.flush()
        return stage

    async def add_stage_entry(
        self, stage_id: UUID, body: StageEntryCreate, user_id: UUID,
    ) -> ProductionStageEntry:
        now = datetime.now(timezone.utc)
        entry = ProductionStageEntry(
            stage_id=stage_id, entry_date=body.entry_date,
            pieces_in=body.pieces_in, pieces_out=body.pieces_out, rejected=body.rejected,
            operator=body.operator, machine=body.machine, notes=body.notes,
            created_at=now, created_by=user_id,
        )
        self.db.add(entry)
        await self.db.flush()

        # Roll up to stage totals
        stage_res = await self.db.execute(select(ProductionStage).where(ProductionStage.id == stage_id))
        stage = stage_res.scalar_one_or_none()
        if stage:
            stage.input_qty += body.pieces_in
            stage.output_qty += body.pieces_out
            stage.rejected_qty += body.rejected
            stage.updated_at = now
            if stage.status == "pending" and body.pieces_in > 0:
                stage.status = "in_progress"
                stage.started_at = now

        await self.db.flush()
        return entry

    # ── Material Issues (MIS) ──────────────────────────────────────────────

    async def list_mis(
        self, company_id: UUID, lot_id: UUID | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[MaterialIssue], int]:
        q = (
            select(MaterialIssue)
            .where(MaterialIssue.company_id == company_id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        if lot_id:
            q = q.where(MaterialIssue.production_lot_id == lot_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(MaterialIssue.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def get_mis(self, mis_id: UUID, company_id: UUID) -> MaterialIssue | None:
        result = await self.db.execute(
            select(MaterialIssue)
            .where(MaterialIssue.id == mis_id, MaterialIssue.company_id == company_id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        return result.scalar_one_or_none()

    async def create_mis(self, body: MaterialIssueCreate, company_id: UUID, user_id: UUID) -> MaterialIssue:
        now = datetime.now(timezone.utc)
        issue_number = await _next_seq(self.db, "MIS", company_id, MaterialIssue)

        mis = MaterialIssue(
            company_id=company_id, issue_number=issue_number,
            production_lot_id=body.production_lot_id, stage_id=body.stage_id,
            warehouse_id=body.warehouse_id, issue_date=body.issue_date,
            notes=body.notes, created_by=user_id, created_at=now,
        )
        self.db.add(mis)
        await self.db.flush()

        for item_data in body.items:
            total_cost = (item_data.issued_qty * item_data.unit_cost).quantize(Decimal("0.01"))
            inv_txn = await self.inv.issue(
                IssueParams(
                    company_id=company_id,
                    product_id=item_data.product_id,
                    variant_id=item_data.variant_id,
                    warehouse_id=body.warehouse_id,
                    quantity=item_data.issued_qty,
                    unit_id=item_data.unit_id,
                    unit_cost=item_data.unit_cost,
                    material_type="raw_material",
                    transaction_date=body.issue_date,
                    reference_type="material_issue",
                    reference_id=mis.id,
                    notes=f"MIS {issue_number}",
                ),
                user_id=user_id,
            )
            await self.db.flush()

            self.db.add(MaterialIssueItem(
                material_issue_id=mis.id,
                product_id=item_data.product_id,
                variant_id=item_data.variant_id,
                planned_qty=item_data.planned_qty,
                issued_qty=item_data.issued_qty,
                unit_id=item_data.unit_id,
                unit_cost=item_data.unit_cost,
                total_cost=total_cost,
                inv_transaction_id=inv_txn.id,
            ))

        await self.db.flush()

        # Advance lot status to in_production if still at planned/approved
        lot_res = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == body.production_lot_id)
        )
        lot = lot_res.scalar_one_or_none()
        if lot and lot.status in ("draft", "planned", "approved", "material_pending"):
            lot.status = "in_production"
            lot.updated_at = now

        await self.db.flush()

        result = await self.db.execute(
            select(MaterialIssue).where(MaterialIssue.id == mis.id)
            .options(selectinload(MaterialIssue.production_lot), selectinload(MaterialIssue.items))
        )
        return result.scalar_one()

    # ── Production Output (FG receive) ─────────────────────────────────────

    async def list_outputs(
        self, company_id: UUID, lot_id: UUID | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[ProductionOutput], int]:
        q = (
            select(ProductionOutput)
            .where(ProductionOutput.company_id == company_id)
            .options(selectinload(ProductionOutput.production_lot))
        )
        if lot_id:
            q = q.where(ProductionOutput.production_lot_id == lot_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(ProductionOutput.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return (await self.db.execute(q)).scalars().all(), total

    async def create_output(
        self, body: ProductionOutputCreate, company_id: UUID, user_id: UUID,
    ) -> ProductionOutput:
        now = datetime.now(timezone.utc)
        output_number = await _next_seq(self.db, "OUT", company_id, ProductionOutput)
        total_cost = (body.quantity * body.unit_cost).quantize(Decimal("0.01"))

        inv_txn = await self.inv.receive(
            ReceiveParams(
                company_id=company_id,
                product_id=body.product_id,
                warehouse_id=body.warehouse_id,
                quantity=body.quantity,
                unit_id=body.unit_id,
                unit_cost=body.unit_cost,
                material_type="finished_good",
                transaction_date=body.output_date,
                reference_type="production_output",
                reference_id=None,
                notes=f"OUT {output_number}",
            ),
            user_id=user_id,
        )
        await self.db.flush()

        output = ProductionOutput(
            company_id=company_id, output_number=output_number,
            production_lot_id=body.production_lot_id, warehouse_id=body.warehouse_id,
            output_date=body.output_date, product_id=body.product_id,
            quantity=body.quantity, unit_id=body.unit_id,
            unit_cost=body.unit_cost, total_cost=total_cost,
            inv_transaction_id=inv_txn.id,
            created_by=user_id, created_at=now,
        )
        self.db.add(output)
        await self.db.flush()

        # Update lot actual_qty
        lot_res = await self.db.execute(
            select(ProductionLot).where(ProductionLot.id == body.production_lot_id)
        )
        lot = lot_res.scalar_one_or_none()
        if lot:
            lot.actual_qty += int(body.quantity)
            lot.updated_at = now

        await self.db.flush()

        result = await self.db.execute(
            select(ProductionOutput).where(ProductionOutput.id == output.id)
            .options(selectinload(ProductionOutput.production_lot))
        )
        return result.scalar_one()
