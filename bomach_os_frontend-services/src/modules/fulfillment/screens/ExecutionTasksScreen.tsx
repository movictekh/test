import type { ExecutionTask } from '../types/fulfillment.types'
import { taskBoardColumns } from '../workspaces/fulfillment-workflow.rules'

function priorityClass(priority: ExecutionTask['priority']) {
  if (priority === 'Critical') return 'fulfillment-pill-red'
  if (priority === 'High') return 'fulfillment-pill-yellow'
  return 'fulfillment-pill-gray'
}

export function ExecutionTasksScreen({
  tasks,
  onOpenTask,
}: {
  tasks: ExecutionTask[]
  onOpenTask: (task: ExecutionTask) => void
}) {
  return (
    <main className="fulfillment-content">
      <section className="fulfillment-card">
        <header className="fulfillment-card-header">
          <div>
            <div className="fulfillment-card-title">Execution Task Board</div>
            <div className="fulfillment-card-subtitle">
              Tasks from workflows, inspections and handoffs
            </div>
          </div>
        </header>

        <div className="fulfillment-kanban">
          {taskBoardColumns.map((column) => {
            const columnTasks = tasks.filter((task) =>
              column === 'To Do'
                ? task.status === column || task.status === 'Blocked'
                : task.status === column,
            )

            return (
              <section className="fulfillment-column" key={column}>
                <div className="fulfillment-column-header">
                  <span>{column}</span>
                  <span>{columnTasks.length}</span>
                </div>

                {columnTasks.length > 0 ? (
                  columnTasks.map((task) => (
                    <button
                      type="button"
                      className="fulfillment-task-card"
                      key={task.id}
                      onClick={() => onOpenTask(task)}
                      title="Open task details"
                    >
                      <b>{task.title}</b>
                      <small>
                        {task.orderId} · {task.owner}
                      </small>
                      <div className="fulfillment-task-footer">
                        <span className={`fulfillment-pill ${priorityClass(task.priority)}`}>
                          {task.status === 'Blocked' ? 'Blocked' : task.priority}
                        </span>
                        <span className="fulfillment-row-sub">{task.dueAt}</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="fulfillment-empty fulfillment-empty-column">No tasks</div>
                )}
              </section>
            )
          })}
        </div>
      </section>
    </main>
  )
}
