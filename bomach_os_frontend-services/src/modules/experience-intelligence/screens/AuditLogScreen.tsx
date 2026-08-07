import { RecordLink } from '@/shared/navigation'
import { downloadCsv } from '../lib/csv'
import type { AuditEvent } from '../types/experience-intelligence.types'

export function AuditLogScreen({ events }: { events: AuditEvent[] }) {
  return (
    <main className="experience-content">
      <section className="experience-card">
        <header className="experience-card-header">
          <div>
            <div className="experience-card-title">Audit & Activity Log</div>
            <div className="experience-card-subtitle">Permanent accountability record</div>
          </div>
          <button
            type="button"
            className="experience-btn"
            onClick={() =>
              downloadCsv(
                'audit-log.csv',
                ['Date & Time', 'User / Role', 'Area', 'Action'],
                events.map((item) => [item.occurredAt, item.actor, item.area, item.action]),
              )
            }
          >
            Export
          </button>
        </header>

        <div className="experience-table-wrap">
          <table className="experience-table experience-audit-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>User / Role</th>
                <th>Area</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {events.map((item) => (
                <tr key={item.id}>
                  <td>{item.occurredAt}</td>
                  <td>{item.actor}</td>
                  <td>{item.area}</td>
                  <td>
                    {item.entityType && item.entityId ? (
                      <RecordLink entityType={item.entityType} entityId={item.entityId}>
                        {item.action}
                      </RecordLink>
                    ) : (
                      item.action
                    )}
                  </td>
                </tr>
              ))}
              {events.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <div className="experience-empty">No audit events.</div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
