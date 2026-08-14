"""Quotation lifecycle, state transitions and quote-to-invoice conversion."""
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from domains.service_operations.models import Invoice,InvoiceItem,Quote,ServiceRequest
from domains.service_operations.services.requests import log_activity
ACTIVE_INVOICE_STATUSES={'draft','sent','viewed','partially_paid','paid','overdue'}

def prepare_data(payload,request_obj=None):
    d=payload.dict(exclude_unset=True)
    if not d.get('required_approver_role_id'): raise ValidationError({'required_approver_role_id':'Required approver role is required.'})
    if d.get('service_fee') is None:
        if d.get('amount') is not None: d['service_fee']=d['amount']
        elif request_obj is not None: d['service_fee']=request_obj.estimated_value
        else: raise ValidationError({'service_fee':'Service fee is required.'})
    if request_obj is not None:
        d['amount']=Decimal('0.00'); d['description']=d.get('description') or request_obj.scope_summary or request_obj.service.name; d['scope_summary']=d.get('scope_summary') or request_obj.scope_summary; d['terms']=d.get('terms') or 'Work begins after the required mobilisation payment and approved documents are received.'; d['valid_until']=d.get('valid_until') or timezone.localdate()+timedelta(days=14)
    elif d.get('amount') is None: d['amount']=Decimal('0.00')
    d['status']='awaiting_approval'; return d

def latest_rejected(req): return req.quotes.filter(status='rejected').order_by('-version','-created_at','-id').first()
def ensure_no_active(req):
    if req.quotes.exclude(status__in=['rejected','expired']).exists(): raise ValidationError('This service request already has an active quote.')

def create_request_quote(req,payload,*,created_by):
    with transaction.atomic():
        ensure_no_active(req); prev=latest_rejected(req); q=Quote.objects.create(client=req.client,service=req.service,service_request=req,previous_quote=prev,version=prev.version+1 if prev else 1,created_by=created_by,**prepare_data(payload,req)); req.quote=q; req.status='under_review'; req.next_action=f'Approve quotation {q.quote_number}'; req.save(update_fields=['quote','status','next_action','updated_at']); log_activity(req,'quote_prepared',f'Quotation {q.quote_number} prepared for {q.amount} and awaiting approval.',created_by=created_by,next_action='Await quote approval'); return q

def create_quote(payload,*,created_by):
    d=prepare_data(payload); req=None; prev=None
    if d.get('service_request_id'):
        req=get_object_or_404(ServiceRequest,id=d['service_request_id']); ensure_no_active(req); d['client_id']=req.client_id; d['service_id']=req.service_id; prev=latest_rejected(req); d['version']=prev.version+1 if prev else 1
    elif d.get('previous_quote_id'): prev=get_object_or_404(Quote,id=d['previous_quote_id']); d['version']=prev.version+1
    d.pop('previous_quote_id',None)
    with transaction.atomic():
        q=Quote.objects.create(previous_quote=prev,created_by=created_by,**d)
        if req: req.quote=q; req.status='under_review'; req.next_action=f'Approve quotation {q.quote_number}'; req.save(update_fields=['quote','status','next_action','updated_at']); log_activity(req,'quote_prepared',f'Quotation {q.quote_number} prepared for {q.amount} and awaiting approval.',created_by=created_by,next_action='Await quote approval')
    return q

def _send(q):
    recipient=q.service_request.contact_email if q.service_request and q.service_request.contact_email else q.client.user.email
    if not recipient: raise ValidationError('Client email is not available.')
    base=getattr(settings,'FRONTEND_PRODUCTION_DOMAIN','').strip().split(); url=''
    if base: url=base[0] if base[0].startswith(('http://','https://')) else 'https://'+base[0]; url=f"{url.rstrip('/')}/service-requests/quotes/{q.id}"
    body=f"Hello {q.client.user.get_full_name() or q.client.user.email},\n\nYour quotation {q.quote_number} for {q.service.name} has been sent.\n\nTotal: {q.amount}\nRequired deposit: {q.deposit_amount}\nValid until: {q.valid_until}\n"+(f"\nView and respond to the quote here: {url}\n" if url else '')+'\nBomach Group'
    send_mail(subject=f'Quotation {q.quote_number} from Bomach Group',message=body,from_email=getattr(settings,'DEFAULT_FROM_EMAIL',None),recipient_list=[recipient],fail_silently=False)

def approve_quote(q,*,employee,user):
    if q.status!='awaiting_approval': raise ValidationError('Only quotes awaiting approval can be approved.')
    if not q.required_approver_role_id: raise ValidationError('Quote has no required approver role.')
    if employee.role_id!=q.required_approver_role_id: raise PermissionError('This quote requires approval from a different role.')
    with transaction.atomic():
        q.status='sent'; q.approved_by=user; q.approved_at=timezone.now(); q.sent_at=q.approved_at; q.save()
        if q.service_request: q.service_request.status='quoted'; q.service_request.next_action='Client to accept or reject quotation'; q.service_request.save(update_fields=['status','next_action','updated_at']); log_activity(q.service_request,'quote_sent',f'Quotation {q.quote_number} approved and sent to client.',created_by=user,next_action='Await client quote response')
    try: _send(q)
    except Exception as e:
        if q.service_request: log_activity(q.service_request,'internal_note',f'Quote email delivery failed for {q.quote_number}: {e}',created_by=user,next_action='Follow up with client manually')
    return q

def create_invoice_from_quote(q,payload,*,user):
    if q.status!='accepted': raise ValidationError('Invoices can only be created from accepted quotes.')
    if q.invoices.filter(status__in=ACTIVE_INVOICE_STATUSES).exists(): raise ValidationError('This quote already has an active invoice.')
    with transaction.atomic():
        i=Invoice.objects.create(client=q.client,service=q.service,quote=q,service_request=q.service_request,issue_date=timezone.localdate(),due_date=payload.due_date,subtotal=q.subtotal or q.amount,tax_rate=q.tax_rate,status='draft',payment_schedule=payload.payment_schedule,payment_instructions=payload.payment_instructions,activation_threshold_amount=q.deposit_amount,notes=payload.notes or q.terms,created_by=user); InvoiceItem.objects.create(invoice=i,description=q.description or q.service.name,quantity=1,unit_price=i.subtotal)
        if q.service_request: q.service_request.next_action=f'Send invoice {i.invoice_number}'; q.service_request.save(update_fields=['next_action','updated_at'])
    return i

def update_quote(q,payload):
    if q.status!='awaiting_approval': raise ValidationError('Only quotes awaiting approval can be edited.')
    for a,v in payload.dict(exclude_unset=True).items(): setattr(q,a,v)
    q.save(); return q

def delete_quote(q):
    if q.service_request_id: raise ValidationError('Service request quotes cannot be deleted.')
    if q.status=='rejected': raise ValidationError('Rejected quotes are immutable and cannot be deleted.')
    q.delete()

def client_accept(q,*,user):
    if q.status!='sent': raise ValidationError('Only sent quotes can be accepted.')
    with transaction.atomic():
        q.status='accepted'; q.client_responded_at=timezone.now(); q.save(update_fields=['status','client_responded_at','updated_at'])
        if q.service_request: q.service_request.next_action='Create invoice for accepted quotation'; q.service_request.save(update_fields=['next_action','updated_at']); log_activity(q.service_request,'quote_accepted',f'Client accepted quotation {q.quote_number}.',created_by=user,next_action='Create invoice')
    return q

def client_reject(q,*,reason,user):
    if q.status!='sent': raise ValidationError('Only sent quotes can be rejected.')
    with transaction.atomic():
        q.status='rejected'; q.client_rejection_reason=reason or ''; q.client_responded_at=timezone.now(); q.save(update_fields=['status','client_rejection_reason','client_responded_at','updated_at'])
        if q.service_request: q.service_request.status='under_review'; q.service_request.next_action='Prepare revised quotation'; q.service_request.save(update_fields=['status','next_action','updated_at']); log_activity(q.service_request,'quote_rejected',f'Client rejected quotation {q.quote_number}.',created_by=user,next_action='Prepare revised quote')
    return q
