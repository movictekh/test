"""Meaningful Service Request mutations and multi-model coordination."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from domains.service_operations.models import Service,ServiceRequest,ServiceRequestActivity,ServiceRequestAnswer,ServiceRequestAttachment,ServiceSubService

def ensure_choice(value, choices, field_name):
    values={c[0] for c in choices}
    if value and value not in values: raise ValidationError({field_name:f"Invalid {field_name}: {value}."})

def log_activity(service_request,activity_type,note,*,created_by=None,outcome='not_applicable',next_action='',next_follow_up_at=None):
    if not service_request: return None
    ensure_choice(activity_type,ServiceRequestActivity.ACTIVITY_TYPE_CHOICES,'activity_type')
    ensure_choice(outcome,ServiceRequestActivity.OUTCOME_CHOICES,'outcome')
    return ServiceRequestActivity.objects.create(request=service_request,activity_type=activity_type,outcome=outcome,note=note,next_action=next_action or '',next_follow_up_at=next_follow_up_at,created_by=created_by)

def _create_answer_rows(obj):
    rows=[ServiceRequestAnswer(request=obj,field_id=f.get('id'),field_key=f['key'],label=f['label'],field_type=f['field_type'],value=obj.answers_snapshot.get(f['key']),sort_order=f.get('sort_order',0)) for f in obj.form_snapshot.get('fields',[])]
    ServiceRequestAnswer.objects.bulk_create(rows)

def create_service_request(payload,*,client,created_by,submitted_by=None,staff=False):
    data=payload.dict(); answers=data.pop('answers')
    rel={'subservice_id':data.pop('subservice_id',None),'branch_id':data.pop('branch_id',None),'service_lead_id':data.pop('service_lead_id',None) if staff else None,'crm_lead_id':data.pop('crm_lead_id',None) if staff else None,'owner_id':data.pop('owner_id',None) if staff else None}
    data.pop('client_id',None); service=get_object_or_404(Service,id=data.pop('service_id')); sub=None
    if rel['subservice_id']: sub=get_object_or_404(ServiceSubService,id=rel['subservice_id'],service=service)
    with transaction.atomic():
        obj=ServiceRequest.objects.create(client=client,service=service,subservice=sub,answers_snapshot=answers,created_by=created_by,submitted_by=submitted_by,**{k:v for k,v in rel.items() if k!='subservice_id'},**data)
        _create_answer_rows(obj); log_activity(obj,'request_created','Service request submitted and consent recorded.',created_by=created_by)
    return obj

def update_staff_request(obj,payload,*,updated_by):
    data=payload.dict(exclude_unset=True); old=obj.status
    for p,a in {'branch_id':'branch_id','owner_id':'owner_id','service_lead_id':'service_lead_id','crm_lead_id':'crm_lead_id'}.items():
        if p in data: setattr(obj,a,data.pop(p))
    for a,v in data.items(): setattr(obj,a,v)
    obj.save(); log_activity(obj,'status_change' if old!=obj.status else 'control_update',f"Service request updated. Status: {obj.status}; next action: {obj.next_action}",created_by=updated_by); return obj

def create_request_activity(obj,payload,*,created_by):
    ensure_choice(payload.activity_type,ServiceRequestActivity.ACTIVITY_TYPE_CHOICES,'activity_type'); ensure_choice(payload.outcome,ServiceRequestActivity.OUTCOME_CHOICES,'outcome')
    return log_activity(obj,payload.activity_type,payload.note,created_by=created_by,outcome=payload.outcome,next_action=payload.next_action or '',next_follow_up_at=payload.next_follow_up_at)

def create_request_attachment(obj,payload,*,uploaded_by):
    x=ServiceRequestAttachment(request=obj,uploaded_by=uploaded_by,**payload.dict()); x.full_clean(); x.save(); return x
