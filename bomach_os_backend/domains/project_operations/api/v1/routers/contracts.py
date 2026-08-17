from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations.models import Contract, Project
from user.utils.perm import require_permission

from ..schemas.schemas import (
    ContractCreateSchema,
    ContractOutSchema,
    ContractUpdateSchema,
    MessageSchema,
)

router = Router(tags=["Contracts"])


@router.get(
    "",
    response=List[ContractOutSchema],
    operation_id="operations_api_v1_contracts_list_contracts",
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("contracts", "list")
def list_contracts(
    request,
    project_id: int = None,
    status: str = None,
    contract_type: str = None,
    search: str = None,
):
    """List all contracts with optional filters"""
    contracts = Contract.objects.all()

    if project_id:
        contracts = contracts.filter(project_id=project_id)
    if status:
        contracts = contracts.filter(status=status)
    if contract_type:
        contracts = contracts.filter(contract_type=contract_type)
    if search:
        contracts = contracts.filter(
            Q(name__icontains=search) | Q(contract_number__icontains=search)
        )

    return list(contracts)


@router.get(
    "/{contract_id}",
    response=ContractOutSchema,
    operation_id="operations_api_v1_contracts_get_contract",
)
@require_permission("contracts", "view")
def get_contract(request, contract_id: int):
    """Get a specific contract by ID"""
    contract = get_object_or_404(Contract, id=contract_id)
    return contract


@router.post(
    "",
    response={200: ContractOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_contracts_create_contract",
)
@require_permission("contracts", "create")
def create_contract(request, payload: ContractCreateSchema):
    """Create a new contract"""
    try:
        contract_data = payload.dict()
        project = get_object_or_404(Project, id=contract_data.pop("project_id"))
        contract = Contract.objects.create(project=project, **contract_data)
        return contract
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.put(
    "/{contract_id}",
    response={200: ContractOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_contracts_update_contract",
)
@require_permission("contracts", "update")
def update_contract(request, contract_id: int, payload: ContractUpdateSchema):
    """Update an existing contract"""
    try:
        contract = get_object_or_404(Contract, id=contract_id)

        update_data = payload.dict(exclude_unset=True)
        if "project_id" in update_data:
            project = get_object_or_404(Project, id=update_data.pop("project_id"))
            contract.project = project

        for attr, value in update_data.items():
            setattr(contract, attr, value)

        contract.save()
        return contract
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete(
    "/{contract_id}", operation_id="operations_api_v1_contracts_delete_contract"
)
@require_permission("contracts", "delete")
def delete_contract(request, contract_id: int):
    """Delete a contract"""
    contract = get_object_or_404(Contract, id=contract_id)
    contract.delete()
    return {"detail": "Contract deleted successfully"}
