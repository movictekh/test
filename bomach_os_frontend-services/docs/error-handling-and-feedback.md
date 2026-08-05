# Bomach Error Handling and User Feedback Standard

## 1. Purpose

This document defines how the Bomach Service Operations frontend presents errors, warnings, success messages, validation feedback, and system failures.

The objective is consistency. A user should not receive the same kind of problem as a toast on one page, a field error on another page, and a vague alert somewhere else.

The placement of a message depends on:

1. what failed;
2. where the user was working;
3. whether the message must remain visible;
4. whether the user can correct the problem;
5. whether the page remains usable;
6. whether the system must redirect the user.

## 2. Main rule

Display the message as close as possible to the place where the user can understand and resolve it.

A toast is not the default location for every error.

Use:

- a field message for one invalid field;
- a form-level alert for a submission problem affecting the form;
- a section error state when one section cannot load;
- a page error state when the main page cannot load;
- a toast for temporary feedback about an action when the current page remains usable;
- a redirect and destination-page alert for an expired session;
- a confirmation dialog before a destructive decision, not after it fails.

## 3. Feedback hierarchy

### 3.1 Field-level message

Use a field message when the error belongs to one input and the user can correct that input.

Examples:

- Email is required.
- Enter a valid phone number.
- End date must be after start date.
- Budget must be greater than zero.
- This service code is already in use.

The message appears beneath or beside the field through `FormControl`.

Do not also show the same field error in a toast.

### 3.2 Form-level alert

Use a persistent form alert when:

- credentials are invalid;
- the submission has a business-rule failure;
- several fields are involved;
- the backend rejects the whole form;
- the user needs the message while correcting the form;
- the form remains open after failure.

Examples:

- The email address or password is incorrect.
- This quotation cannot be submitted because no approval route is configured.
- The request cannot be created until a client is selected.
- The verification code is incorrect or expired.
- The record has changed. Reload the latest version before submitting again.

The alert appears above the form or immediately before the action area.

Login errors belong here, not in a toast, because the user remains on the login form and needs the message while correcting the credentials.

### 3.3 Toast

Use a toast for brief feedback about a completed or failed action when:

- the user remains on a usable page;
- the message does not require editing a particular field;
- the feedback is temporary;
- the action was initiated from a button, menu, table row, drawer, or background interaction;
- the page content still provides the main context.

Suitable success examples:

- Request assigned.
- Draft saved.
- Notification marked as read.
- Link copied.
- File removed.
- Task moved to In Progress.

Suitable error examples:

- The request could not be assigned.
- The notification could not be marked as read.
- The file could not be removed.
- The task could not be moved because it has changed.
- The server could not be reached while refreshing this section.

Do not use a toast for:

- field validation;
- invalid login credentials;
- a completely broken page;
- a completely broken section;
- a message the user must read before continuing;
- a long explanation;
- session expiry where the user is being redirected;
- destructive confirmation.

### 3.4 Inline persistent Alert

Use `Alert` for information that must remain visible while the user works.

Examples:

- Your session expired. Sign in again to continue.
- This quotation requires management approval.
- This order cannot start until the mobilisation payment is confirmed.
- Changes to pricing will affect future quotations only.
- This account is disabled.

Alerts may be `info`, `warning`, `danger`, or `success`, depending on meaning.

### 3.5 Section error state

Use `SectionErrorState` when one part of a page fails but the rest of the page still works.

Examples:

- Request activity could not be loaded.
- Payment history is unavailable.
- Deliverables could not be loaded.
- Dashboard finance metrics could not be refreshed.

The section error should normally include a retry action.

Do not replace the entire page with an error when only one section failed.

### 3.6 Page error state

Use `ErrorState` when the page's main record or primary dataset cannot load.

Examples:

- Request details could not be loaded.
- Service catalogue could not be loaded.
- This report is temporarily unavailable.

The page error should normally provide:

- a clear title;
- a useful description;
- Retry where appropriate;
- Back or return navigation where appropriate.

### 3.7 Forbidden and unauthorized

`401 Unauthorized` means there is no valid authenticated session.

The frontend should:

1. clear authentication state;
2. redirect to login;
3. show a session-expired message where appropriate;
4. preserve only a validated internal return route.

Do not show a normal error toast and leave the user on a protected screen.

`403 Forbidden` means the user is authenticated but lacks permission.

For a route, show the Forbidden page.

For a single action on an otherwise usable page, show a danger toast:

- You do not have permission to approve this quotation.

The backend remains the authority even when the frontend hides unavailable actions.

### 3.8 Not found

For the main route record, show a page-level not-found state.

For a secondary action, show a toast where the page remains usable.

User-facing wording:

- This record may have been removed or you may no longer have access to it.

Avoid exposing internal model names or database identifiers.

### 3.9 Conflict and stale data

Use HTTP `409` or an equivalent backend code for conflicts.

Examples:

- another user changed the request;
- a plot was reserved by someone else;
- the quotation version is stale;
- the order status changed before the action completed.

Show:

- a form alert when submitting a form;
- a toast for a row action or background action;
- a reload or refresh action where useful.

User-facing wording:

- The record has changed. Refresh the latest information before trying again.

Do not silently overwrite newer server data.

## 4. Toast tones

### Success toast

Use after a small action is confirmed by the backend.

Examples:

- Draft saved.
- Request assigned.
- Payment note added.

Do not show success before a sensitive mutation is confirmed.

### Error toast

Use when a temporary action fails and the page remains usable.

Examples:

- Assignment failed.
- File removal failed.
- Could not update notification.

### Warning toast

Use for a non-fatal condition requiring attention.

Examples:

- Changes were saved, but one notification could not be sent.
- The export is taking longer than expected.
- Some selected records were skipped.

### Information toast

Use for neutral temporary information.

Examples:

- Export preparation started.
- Link copied to clipboard.
- Background refresh completed.

## 5. Authentication messages

Authentication messages must be helpful without revealing whether an account exists.

### Invalid email or password

Use:

> The email address or password is incorrect. Check both and try again.

Do not use:

- Account not found.
- This email does not exist.
- Password is wrong.
- User exists, but the password is invalid.

Those messages expose account-registration information and create inconsistent login behaviour.

### Disabled or inactive account

When the backend deliberately exposes an inactive-account condition, use:

> This account is not currently active. Contact an administrator for assistance.

Do not display backend implementation terms such as `is_active=false`.

### Too many attempts

Use:

> Too many login attempts. Please wait a moment before trying again.

### Network failure

Use:

> We could not reach the server. Check your connection and try again.

### Server failure

Use:

> The sign-in service is temporarily unavailable. Please try again shortly.

### Two-factor code error

Use:

> The verification code is incorrect or has expired. Enter a new code and try again.

These authentication errors remain visible as a form-level Alert. They are not toasts.

## 6. Backend error translation

The UI must not display arbitrary backend text directly.

Backend messages may contain:

- serializer wording;
- field names;
- model names;
- internal status names;
- database details;
- stack information;
- inconsistent punctuation;
- wording unsuitable for clients.

The frontend should translate errors through the shared `presentError()` utility.

The utility considers:

- HTTP status;
- backend error code;
- backend detail;
- error context;
- validation details.

It returns:

```ts
{
  title: string
  message: string
  placement: 'field' | 'form' | 'toast' | 'section' | 'page' | 'redirect'
  retryable: boolean
  fieldErrors?: Record<string, string>
}
```

Feature code should choose an error context such as:

- `login`
- `two-factor`
- `form-submit`
- `page-load`
- `section-load`
- `background-action`
- `destructive-action`

## 7. HTTP status guidance

### Status 400 or 422

Usually validation or malformed input.

Show field messages where field details exist. Otherwise show a form-level alert.

### Status 401

Treat as session expiry outside the login endpoint.

Clear session, redirect, and show the login-page expiry alert.

For login itself, translate to the neutral invalid-credentials message.

### Status 403

Route-level denial uses Forbidden.

Action-level denial uses a toast or persistent alert depending on whether the restriction remains relevant.

### Status 404

Main record uses page not-found state.

Secondary action uses a toast.

### Status 409

Show stale-data or business-conflict feedback near the action and offer refresh where useful.

### Status 429

Show a wait-and-retry message. Keep it near the form for login or submission; otherwise use a toast.

### Status 500–599

Do not expose raw server text.

Use page, section, form, or toast placement according to what failed.

### Status 0 or network error

Explain that the server could not be reached and offer retry.

## 8. Success-message rules

Use a toast when:

- the action was small;
- the result is already visible in the page;
- the user does not need a dedicated completion page.

Use `SuccessState` when:

- a major journey has completed;
- the user needs a reference number;
- next steps must be explained;
- the user must choose where to continue.

Examples for `SuccessState`:

- Service request created.
- Quotation submitted for approval.
- Payment confirmation completed.
- Service order completed.

Avoid showing both a success state and a duplicate success toast.

## 9. Duplication rules

Never show the same error in more than one place.

Bad:

- field message;
- form alert;
- error toast;
- console alert;

all for the same validation failure.

Good:

- field messages for specific fields;
- one form alert only when there is also a form-wide problem.

A page-level error should not also produce a toast unless a separate background action failed.

## 10. Logging and diagnostics

User-facing messages should be safe and understandable.

Diagnostic information belongs in development logging or observability, including:

- HTTP status;
- backend code;
- endpoint;
- request ID or correlation ID;
- safe error details;
- stack trace;
- build version.

Never log:

- passwords;
- access tokens;
- refresh tokens;
- two-factor codes;
- private document contents;
- sensitive personal data without an approved reason.

## 11. Examples

### Form submission

```ts
const presentation = presentError(error, 'form-submit')

if (presentation.fieldErrors) {
  applyServerFieldErrors(presentation.fieldErrors)
}

setFormError(presentation.message)
```

### Background action

```ts
const presentation = presentError(error, 'background-action')

toast.error(presentation.title, {
  description: presentation.message,
})
```

### Page query

```tsx
if (query.isError) {
  const presentation = presentError(query.error, 'page-load')

  return (
    <ErrorState
      title={presentation.title}
      description={presentation.message}
      actionLabel="Try again"
      onAction={() => void query.refetch()}
    />
  )
}
```

### Section query

```tsx
if (query.isError) {
  const presentation = presentError(query.error, 'section-load')

  return (
    <SectionErrorState
      title={presentation.title}
      description={presentation.message}
      onRetry={() => void query.refetch()}
    />
  )
}
```

## 12. Review checklist

Before approving a feature, confirm:

- the message appears close to the failed action;
- field validation is not shown as a toast;
- login errors are form-level;
- page failures use page states;
- section failures use section states;
- action failures use toasts only when the page remains usable;
- raw backend messages are translated;
- unauthorized and forbidden are treated differently;
- messages do not expose account existence;
- messages do not expose technical details;
- success is not shown before server confirmation;
- duplicate feedback is not displayed;
- retry is offered only when retrying can help.
