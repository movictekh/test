from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from ninja import Schema
class FixedAssetCategoryIn(Schema):
    code:str; name:str; description:str=''; asset_ledger_account_id:int; accumulated_depreciation_ledger_account_id:int; depreciation_expense_ledger_account_id:int; default_useful_life_months:int; default_residual_value_percent:Decimal=Decimal('0.00')
class FixedAssetCategoryUpdate(Schema):
    name:Optional[str]=None; description:Optional[str]=None; asset_ledger_account_id:Optional[int]=None; accumulated_depreciation_ledger_account_id:Optional[int]=None; depreciation_expense_ledger_account_id:Optional[int]=None; default_useful_life_months:Optional[int]=None; default_residual_value_percent:Optional[Decimal]=None
class FixedAssetCategoryOut(Schema):
    id:int; code:str; name:str; description:str; asset_ledger_account_id:int; accumulated_depreciation_ledger_account_id:int; depreciation_expense_ledger_account_id:int; default_useful_life_months:int; default_residual_value_percent:Decimal; default_depreciation_method:str; is_active:bool; created_by_id:Optional[int]=None; created_at:datetime; updated_at:datetime
class FixedAssetIn(Schema):
    category_id:int; source_expense_id:int; name:str; description:str=''; acquisition_date:date; acquisition_cost:Decimal; residual_value:Optional[Decimal]=None; useful_life_months:Optional[int]=None; branch_id:Optional[int]=None
class FixedAssetUpdate(Schema):
    name:Optional[str]=None; description:Optional[str]=None; residual_value:Optional[Decimal]=None; useful_life_months:Optional[int]=None
class FixedAssetCapitalizeIn(Schema): capitalization_date:Optional[date]=None
class FixedAssetDepreciateIn(Schema): period_end:date
class FixedAssetDisposeIn(Schema):
    disposal_date:date; proceeds:Decimal=Decimal('0.00'); finance_account_id:Optional[int]=None; reference:str=''; notes:str=''
class FixedAssetOut(Schema):
    id:int; asset_number:str; name:str; description:str; category_id:int; category_name:str; branch_id:Optional[int]=None; branch_name:str; source_expense_id:Optional[int]=None; acquisition_date:date; capitalization_date:Optional[date]=None; currency:str; acquisition_cost:Decimal; residual_value:Decimal; useful_life_months:int; depreciation_method:str; status:str; depreciable_amount:Decimal; accumulated_depreciation:Decimal; book_value:Decimal; disposed_at:Optional[date]=None; disposal_proceeds:Optional[Decimal]=None; disposal_finance_account_id:Optional[int]=None; disposal_reference:str; disposal_notes:str; created_by_id:Optional[int]=None; created_at:datetime; updated_at:datetime
class FixedAssetDepreciationScheduleRowOut(Schema):
    period_end:date; depreciation_amount:Decimal; cumulative_depreciation:Decimal; closing_book_value:Decimal; posted:bool
