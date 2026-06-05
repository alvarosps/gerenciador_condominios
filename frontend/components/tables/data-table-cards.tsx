import type { Column } from './data-table';
import { renderCellContent } from './cell-value';

interface DataTableCardsProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  rowKey: (record: T, index: number) => string;
  className?: string;
}

function getTitleColumn<T>(columns: Column<T>[]): Column<T> | undefined {
  return columns.find((column) => column.primary) ?? columns.find((column) => !column.isActions);
}

export function DataTableCards<T extends object>({
  columns,
  data,
  rowKey,
  className,
}: DataTableCardsProps<T>): React.ReactElement {
  if (data.length === 0) {
    return (
      <div className={className}>
        <div className="rounded-md border p-8 text-center">
          <p className="text-muted-foreground">Nenhum dado disponível</p>
        </div>
      </div>
    );
  }

  const titleColumn = getTitleColumn(columns);
  const actionColumns = columns.filter((column) => column.isActions);

  return (
    <div className={className}>
      <div className="space-y-3">
        {data.map((record, index) => {
          const bodyColumns = columns.filter(
            (column) =>
              column !== titleColumn && !column.isActions && !column.hideOnCard
          );

          return (
            <div
              key={rowKey(record, index)}
              data-testid="data-table-card"
              className="rounded-md border p-4 space-y-3"
            >
              {titleColumn && (
                <div data-testid="data-table-card-title" className="font-medium">
                  {renderCellContent(titleColumn, record, index)}
                </div>
              )}

              {bodyColumns.length > 0 && (
                <dl className="space-y-1">
                  {bodyColumns.map((column) => (
                    <div
                      key={column.key}
                      className="flex justify-between gap-2 text-sm"
                    >
                      <dt className="text-muted-foreground">{column.title}</dt>
                      <dd className="text-right">{renderCellContent(column, record, index)}</dd>
                    </div>
                  ))}
                </dl>
              )}

              {actionColumns.length > 0 && (
                <div
                  data-testid="data-table-card-footer"
                  className="flex flex-col gap-2 border-t pt-3"
                >
                  {actionColumns.map((column) => (
                    <div key={column.key} className="w-full">
                      {column.render?.(undefined, record, index)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
