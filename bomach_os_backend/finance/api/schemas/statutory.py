from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from ninja import Schema
class StatutoryObligationIn(Schema):
    obligation_type:str; period_label:str; period_start:date; period_end:date; basis:str; basis_amount:Decimal=Decimal("0.00"); amount:Decimal; due_date:date; branch_id:Optional[int]=None; notes:str=""
class StatutoryObligationUpdate(Schema):
    period_label:Optional[str]=None; period_start:Optional[date]=None; period_end:Optional[date]=None; basis:Optional[str]=None; basis_amount:Optional[Decimal]=None; amount:Optional[Decimal]=None; due_date:Optional[date]=None; notes:Optional[str]=None
class StatutoryRejectIn(Schema): reason:str
class StatutoryPayIn(Schema): finance_account_id:int; paid_at:Optional[datetime]=None; payment_reference:str=""
class WHTGenerateIn(Schema): period_start:date; period_end:date; due_date:date; branch_id:Optional[int]=None; period_label:str=""; notes:str=""
class PayrollStatutoryGenerateIn(Schema): payroll_run_id:int; category:str; due_date:date; notes:str=""
class StatutoryObligationItemOut(Schema): id:int; source_type:str; source_reference:str; description:str; basis_amount:Decimal; liability_amount:Decimal
class StatutoryObligationOut(Schema):
    id:int; obligation_number:str; obligation_type:str; obligation_type_display:str; source_type:str; branch_id:Optional[int]=None; branch_name:str; period_label:str; period_start:date; period_end:date; basis:str; basis_amount:Decimal; amount:Decimal; due_date:date; status:str; status_display:str; is_overdue:bool; finance_account_id:Optional[int]=None; finance_account_name:str; notes:str; submitted_at:Optional[datetime]=None; approved_at:Optional[datetime]=None; rejected_at:Optional[datetime]=None; rejection_reason:str; paid_at:Optional[datetime]=None; payment_reference:str; created_at:datetime; updated_at:datetime
class StatutoryObligationDetailOut(StatutoryObligationOut): items:List[StatutoryObligationItemOut]
class StatutorySummaryOut(Schema): vat_payable:Decimal; wht_payable:Decimal; paye_payable:Decimal; pension_payable:Decimal; other_payable:Decimal; total_payable:Decimal; overdue_amount:Decimal; outstanding_count:int; overdue_count:int
