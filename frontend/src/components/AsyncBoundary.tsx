import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { errorMessage } from '../api/client'
import { EmptyState, ErrorState, Skeleton } from './states'

interface Props<T> {
  query: UseQueryResult<T>
  isEmpty?: (data: T) => boolean
  emptyText?: string
  height?: number
  children: (data: T) => ReactNode
}

/** One place that decides: loading skeleton / error with retry / empty / data. */
export default function AsyncBoundary<T>({
  query,
  isEmpty,
  emptyText = 'No data to show.',
  height,
  children,
}: Props<T>) {
  if (query.data === undefined) {
    if (query.isError) {
      return <ErrorState message={errorMessage(query.error)} onRetry={() => query.refetch()} />
    }
    return <Skeleton height={height} />
  }
  if (isEmpty?.(query.data)) return <EmptyState text={emptyText} />
  return <>{children(query.data)}</>
}
