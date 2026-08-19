from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from ninja import Schema
class BankReconciliationIn(Schema):
    finance_account_id:int; statement_start_date:date; statement_end_date:date; statement_opening_balance:Decimal; statement_closing_balance:Decimal; notes:str=''
class BankStatementLineIn(Schema):
    transaction_date:date; value_date:Optional[date]=None; description:str=''; reference:str=''; amount:Decimal; direction:str; running_balance:Optional[Decimal]=None; external_transaction_id:str=''; sequence_number:int
class BankStatementLinesIn(Schema): lines:List[BankStatementLineIn]
class BankReconciliationMatchIn(Schema): bank_statement_line_id:int; journal_line_id:int; matched_amount:Decimal; notes:str=''
class BankReconciliationOut(Schema):
    id:int; finance_account_id:int; finance_account_name:str; statement_start_date:date; statement_end_date:date; statement_opening_balance:Decimal; statement_closing_balance:Decimal; status:str; notes:str; reconciled_by_id:Optional[int]=None; reconciled_at:Optional[datetime]=None; closed_by_id:Optional[int]=None; closed_at:Optional[datetime]=None; created_by_id:Optional[int]=None; created_at:datetime; updated_at:datetime
class BankStatementLineOut(Schema):
    id:int; transaction_date:date; value_date:Optional[date]=None; description:str; reference:str; amount:Decimal; direction:str; running_balance:Optional[Decimal]=None; external_transaction_id:str; sequence_number:int; matched_amount:Decimal; remaining_amount:Decimal
class BankReconciliationMatchOut(Schema):
    id:int; bank_statement_line_id:int; journal_line_id:int; matched_amount:Decimal; match_type:str; matched_by_id:Optional[int]=None; matched_at:datetime; notes:str
class BankGLCandidateOut(Schema):
    journal_line_id:int; journal_entry_id:int; journal_number:str; entry_date:date; reference:str; description:str; direction:str; movement_amount:Decimal; remaining_amount:Decimal
class BankReconciliationSummaryOut(Schema):
    statement_opening_balance:Decimal; statement_credits:Decimal; statement_debits:Decimal; calculated_statement_closing_balance:Decimal; statement_closing_balance:Decimal; statement_internal_difference:Decimal; book_closing_balance:Decimal; outstanding_gl_net:Decimal; adjusted_statement_balance:Decimal; unexplained_difference:Decimal; unmatched_statement_amount:Decimal; unmatched_statement_count:int; unmatched_gl_amount:Decimal; unmatched_gl_count:int
