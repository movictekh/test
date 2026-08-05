# Bomach Frontend Design System

## Purpose

This document defines the shared visual and interaction rules used by the Bomach Service Operations frontend.

Business modules should reuse these components instead of creating new visual versions of the same control.

## Semantic design language

Components use semantic meaning:

- `primary`
- `secondary`
- `success`
- `warning`
- `danger`
- `neutral`
- `info`

Component APIs should not use raw colour names such as `blueButton`, `greenBadge`, or `redPanel`.

## Component ownership

### Shared UI

A component belongs in `src/shared/ui` when it:

- has no Bomach business rules;
- is useful across more than one module;
- owns a reusable visual or interaction pattern;
- has clear props and stable behaviour.

### Domain components

A component stays inside its business module when it understands records such as requests, quotations, invoices, service orders, deliverables, or estate plots.

Examples:

- `RequestActivityTimeline`
- `QuotationTotals`
- `InvoicePaymentSummary`
- `OrderMilestoneBoard`
- `EstatePlotGrid`

## Core components

The current shared library includes:

- Alert
- Badge
- Breadcrumbs
- Button
- Card
- Checkbox
- ConfirmDialog
- Dialog
- Drawer
- EmptyState
- ErrorState
- FormControl
- Input
- PageHeader
- ProgressBar
- SectionErrorState
- Select
- Skeleton loaders
- Spinner
- StatCard
- StatusBadge
- Stepper
- SuccessState
- Tabs
- Textarea
- Toast
- Tooltip

## State rules

### Loading

Use the skeleton that matches the content:

- `PageSkeleton`
- `DashboardSkeleton`
- `TableSkeleton`
- `FormSkeleton`
- `AppShellSkeleton`

Do not replace a complete page with a skeleton when only one small section is refreshing.

### Empty

Use `EmptyState` for a genuinely empty collection. Use suitable wording and an action where the user can resolve the empty state.

### Error

Use `ErrorState` when the page cannot load. Use `SectionErrorState` when one section fails and the rest of the page remains usable.

### Success

Use `SuccessState` after a major completed journey. Use a toast for a small update.

### Persistent notices

Use `Alert` for information that should remain visible in the page.

### Temporary feedback

Use the toast system for short success, error, warning, and informational feedback.

## Overlay rules

Use:

- `Dialog` for forms, details, previews, and content;
- `ConfirmDialog` for decisions that must be confirmed;
- `Drawer` for notifications, mobile filters, and side-panel workflows;
- `Tooltip` for short supporting information, especially icon-only actions.

Do not use browser `alert()` or `confirm()` in production pages.

## Accessibility

Shared components must provide:

- visible focus;
- correct semantic elements;
- keyboard navigation;
- Escape behaviour for overlays;
- focus trapping and restoration;
- labels for icon-only buttons;
- screen-reader status or alert announcements;
- colour contrast;
- meaning that does not depend on colour alone.

## Storybook

Stable shared components should have stories covering their important variants and states.

Storybook is the visual catalogue of the Bomach design system.

## Showcase route

During development, authenticated staff users can review the design system at:

`/app/design-system`

This route is for development and review. It is not a business module.

## Error and feedback placement

The complete standard is documented in:

`docs/error-handling-and-feedback.md`

Summary:

- field validation belongs beside the field;
- whole-form failures belong in a persistent form Alert;
- temporary action feedback belongs in a toast;
- section loading failures use `SectionErrorState`;
- page loading failures use `ErrorState`;
- expired sessions redirect to login and show a persistent Alert;
- route permission failures use the Forbidden page;
- major completed journeys use `SuccessState`;
- do not display the same message in several places;
- do not show arbitrary backend error text directly.
