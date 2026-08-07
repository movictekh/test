import { RecordLink } from '@/shared/navigation'
import type { FeedbackSummary, ServiceFeedback } from '../types/experience-intelligence.types'

function statusClass(status: ServiceFeedback['status']) {
  if (status === 'Closed') return 'experience-pill-green'
  if (status === 'Action Required') return 'experience-pill-red'
  return 'experience-pill-yellow'
}

export function FeedbackQualityScreen({
  feedback,
  summary,
  onOpen,
}: {
  feedback: ServiceFeedback[]
  summary: FeedbackSummary
  onOpen: (feedback: ServiceFeedback) => void
}) {
  return (
    <main className="experience-content">
      <div className="experience-kpi-grid">
        <article className="experience-kpi-card">
          <div>Average rating</div>
          <strong>{summary.averageRating}/5</strong>
        </article>
        <article className="experience-kpi-card">
          <div>Client satisfaction</div>
          <strong>{summary.clientSatisfaction}%</strong>
        </article>
        <article className="experience-kpi-card">
          <div>Rework rate</div>
          <strong>{summary.reworkRate}%</strong>
        </article>
        <article className="experience-kpi-card">
          <div>Repeat clients</div>
          <strong>{summary.repeatClients}%</strong>
        </article>
      </div>

      <section className="experience-card">
        <header className="experience-card-header">
          <div>
            <div className="experience-card-title">Service Feedback Register</div>
            <div className="experience-card-subtitle">
              Completion feedback, defects, complaints and testimonials
            </div>
          </div>
        </header>

        <div className="experience-table-wrap">
          <table className="experience-table experience-feedback-table">
            <thead>
              <tr>
                <th>Feedback</th>
                <th>Client</th>
                <th>Service</th>
                <th>Order</th>
                <th>Rating</th>
                <th>Type</th>
                <th>Comment</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {feedback.map((item) => (
                <tr
                  key={item.id}
                  tabIndex={0}
                  className="experience-clickable-row"
                  onClick={() => onOpen(item)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onOpen(item)
                    }
                  }}
                >
                  <td>
                    <b>{item.id}</b>
                    <div className="experience-row-sub">{item.date}</div>
                  </td>
                  <td>{item.client}</td>
                  <td>{item.service}</td>
                  <td>
                    <RecordLink entityType="order" entityId={item.orderId}>
                      {item.orderId}
                    </RecordLink>
                  </td>
                  <td>{item.rating}/5</td>
                  <td>{item.type}</td>
                  <td className="experience-comment-cell">{item.comment}</td>
                  <td>
                    <span className={`experience-pill ${statusClass(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
              {feedback.length === 0 ? (
                <tr>
                  <td colSpan={8}>
                    <div className="experience-empty">No feedback recorded.</div>
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
