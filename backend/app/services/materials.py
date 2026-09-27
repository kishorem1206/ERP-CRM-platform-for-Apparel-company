"""MaterialsService: create yarn, fabric, trim lots and fabric runs."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import FabricRun, FabricVariant, InventoryLot, MaterialCompositionItem, TrimVariant
from app.schemas.inventory import ReceiveParams
from app.schemas.materials import FabricCreate, FabricRunCreate, TrimCreate, YarnCreate
from app.services.inventory import InventoryService


class MaterialsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv = InventoryService(db)

    async def _next_number(self, company_id: UUID, document_type: str) -> str:
        """Concurrency-safe sequence number using document_sequences SELECT FOR UPDATE."""
        result = await self.db.execute(
            text("""
                SELECT prefix, separator, year_format, next_number, padding
                FROM document_sequences
                WHERE company_id = :cid AND document_type = :dtype
                FOR UPDATE
            """),
            {"cid": str(company_id), "dtype": document_type},
        )
        row = result.mappings().first()
        if row is None:
            # Fallback: count existing lots of this type
            count_result = await self.db.execute(
                text("SELECT COUNT(*) FROM inventory_lots WHERE company_id = :cid AND material_type = :mtype"),
                {"cid": str(company_id), "mtype": document_type},
            )
            seq = (count_result.scalar() or 0) + 1
            prefix = {"yarn": "YRN", "fabric": "FAB", "trim": "TRM", "fabric_run": "FR"}.get(document_type, "LOT")
            return f"{prefix}{seq:05d}"

        prefix = row["prefix"] or ""
        sep = row["separator"] or ""
        next_num = row["next_number"]
        padding = row["padding"] or 5
        year_format = row["year_format"] or ""

        year_part = ""
        if year_format:
            now = datetime.now(timezone.utc)
            year_part = now.strftime(year_format) + sep

        number_part = str(next_num).zfill(padding)
        lot_number = f"{prefix}{sep}{year_part}{number_part}"

        await self.db.execute(
            text("UPDATE document_sequences SET next_number = next_number + 1 WHERE company_id = :cid AND document_type = :dtype"),
            {"cid": str(company_id), "dtype": document_type},
        )
        return lot_number

    def _blend_summary(self, compositions: list) -> str:
        return " / ".join(f"{c.fibre_name} {c.percentage}%" for c in compositions) if compositions else ""

    async def create_yarn(self, body: YarnCreate, company_id: UUID, user_id: UUID) -> InventoryLot:
        lot_number = body.lot_number or await self._next_number(company_id, "yarn")
        blend_summary = self._blend_summary(body.compositions)
        fibre_type = body.compositions[0].fibre_name if len(body.compositions) == 1 else ("blend" if body.compositions else None)

        lot = InventoryLot(
            company_id=company_id,
            lot_number=lot_number,
            material_type="yarn",
            supplier_id=body.supplier_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            yarn_count=body.yarn_count,
            ply=body.ply,
            mill=body.mill,
            spinning_type=body.spinning_type,
            treatment=body.treatment,
            colour=body.colour,
            fibre_type=fibre_type,
            blend_composition=blend_summary,
            bags=body.bags,
            kg_per_bag=body.kg_per_bag,
            unit_cost=body.unit_cost,
            notes=body.notes,
            created_by=user_id,
        )
        self.db.add(lot)
        await self.db.flush()

        for comp in body.compositions:
            self.db.add(MaterialCompositionItem(
                inventory_lot_id=lot.id,
                fibre_name=comp.fibre_name,
                percentage=comp.percentage,
            ))

        if body.warehouse_id and body.product_id and body.unit_id and body.bags and body.kg_per_bag:
            quantity = body.bags * body.kg_per_bag
            await self.inv.receive(
                ReceiveParams(
                    company_id=company_id,
                    product_id=body.product_id,
                    warehouse_id=body.warehouse_id,
                    lot_id=lot.id,
                    quantity=quantity,
                    unit_id=body.unit_id,
                    unit_cost=body.unit_cost or Decimal("0"),
                    material_type="yarn",
                    transaction_date=body.transaction_date or date.today(),
                    reference_type="lot",
                    reference_id=lot.id,
                    notes=f"Yarn lot {lot_number} received",
                ),
                user_id=user_id,
            )

        await self.db.flush()
        return lot

    async def create_fabric(self, body: FabricCreate, company_id: UUID, user_id: UUID) -> InventoryLot:
        lot_number = body.lot_number or await self._next_number(company_id, "fabric")
        blend_summary = self._blend_summary(body.compositions)
        fibre_type = body.compositions[0].fibre_name if len(body.compositions) == 1 else ("blend" if body.compositions else None)

        lot = InventoryLot(
            company_id=company_id,
            lot_number=lot_number,
            material_type="fabric",
            supplier_id=body.supplier_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            construction=body.construction,
            gsm=body.gsm,
            diameter_inches=body.diameter_inches,
            colour=body.colour,
            finish=body.finish,
            fibre_type=fibre_type,
            blend_composition=blend_summary,
            split_by_colour=body.split_by_colour,
            split_by_dia=body.split_by_dia,
            unit_cost=body.unit_cost,
            notes=body.notes,
            created_by=user_id,
        )
        self.db.add(lot)
        await self.db.flush()

        for comp in body.compositions:
            self.db.add(MaterialCompositionItem(
                inventory_lot_id=lot.id,
                fibre_name=comp.fibre_name,
                percentage=comp.percentage,
            ))

        for fv in body.fabric_variants:
            self.db.add(FabricVariant(
                inventory_lot_id=lot.id,
                colour=fv.colour,
                dia_inches=fv.dia_inches,
                notes=fv.notes,
            ))

        if body.warehouse_id and body.product_id and body.unit_id and body.quantity:
            await self.inv.receive(
                ReceiveParams(
                    company_id=company_id,
                    product_id=body.product_id,
                    warehouse_id=body.warehouse_id,
                    lot_id=lot.id,
                    quantity=body.quantity,
                    unit_id=body.unit_id,
                    unit_cost=body.unit_cost or Decimal("0"),
                    material_type="fabric",
                    transaction_date=body.transaction_date or date.today(),
                    reference_type="lot",
                    reference_id=lot.id,
                    notes=f"Fabric lot {lot_number} received",
                ),
                user_id=user_id,
            )

        await self.db.flush()
        return lot

    async def create_trim(self, body: TrimCreate, company_id: UUID, user_id: UUID) -> InventoryLot:
        lot_number = body.lot_number or await self._next_number(company_id, "trim")

        lot = InventoryLot(
            company_id=company_id,
            lot_number=lot_number,
            material_type="trim",
            trim_type=body.trim_type,
            trim_unit=body.trim_unit,
            supplier_id=body.supplier_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            colour=body.colour,
            split_by_colour=body.split_by_colour,
            unit_cost=body.unit_cost,
            notes=body.notes,
            created_by=user_id,
        )
        self.db.add(lot)
        await self.db.flush()

        for tv in body.trim_variants:
            self.db.add(TrimVariant(
                inventory_lot_id=lot.id,
                colour=tv.colour,
                notes=tv.notes,
            ))

        if body.warehouse_id and body.product_id and body.unit_id and body.quantity:
            await self.inv.receive(
                ReceiveParams(
                    company_id=company_id,
                    product_id=body.product_id,
                    warehouse_id=body.warehouse_id,
                    lot_id=lot.id,
                    quantity=body.quantity,
                    unit_id=body.unit_id,
                    unit_cost=body.unit_cost or Decimal("0"),
                    material_type="trim",
                    transaction_date=body.transaction_date or date.today(),
                    reference_type="lot",
                    reference_id=lot.id,
                    notes=f"Trim lot {lot_number} received",
                ),
                user_id=user_id,
            )

        await self.db.flush()
        return lot

    async def create_fabric_run(self, body: FabricRunCreate, company_id: UUID, user_id: UUID) -> FabricRun:
        run_number = body.run_number or await self._next_number(company_id, "fabric_run")
        run = FabricRun(
            company_id=company_id,
            run_number=run_number,
            construction=body.construction,
            input_lot_id=body.input_lot_id,
            input_qty=body.input_qty,
            machine=body.machine,
            started_at=body.started_at,
            notes=body.notes,
            status="open",
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def list_lots(
        self, company_id: UUID, material_type: str | None = None,
        trim_type: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[InventoryLot], int]:
        q = select(InventoryLot).where(InventoryLot.company_id == company_id)
        if material_type:
            q = q.where(InventoryLot.material_type == material_type)
        if trim_type:
            q = q.where(InventoryLot.trim_type == trim_type)
        from sqlalchemy import func
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(InventoryLot.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def list_trim_types(self, company_id: UUID) -> list[tuple[str, int]]:
        """Distinct trim types with lot counts, for filter chips on the Trims tab."""
        result = await self.db.execute(
            text("""
                SELECT trim_type, COUNT(*) AS cnt
                FROM inventory_lots
                WHERE company_id = :cid AND material_type = 'trim' AND trim_type IS NOT NULL
                GROUP BY trim_type
                ORDER BY trim_type
            """),
            {"cid": str(company_id)},
        )
        return [(row.trim_type, row.cnt) for row in result.all()]

    async def list_fabric_runs(
        self, company_id: UUID, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list[FabricRun], int]:
        q = select(FabricRun).where(FabricRun.company_id == company_id)
        if status:
            q = q.where(FabricRun.status == status)
        from sqlalchemy import func
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(FabricRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total
