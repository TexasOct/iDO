import { pyInvoke } from 'tauri-plugin-pytauri-api'
import { TimelineDay } from '@/lib/types/activity'

/**
 * 获取每天的活动总数统计（数据库中的实际总数）
 * 这与分页的已加载数据不同，显示的是每天在数据库中的真实记录总数
 */
export async function fetchActivityCountByDate(): Promise<Record<string, number>> {
  try {
    console.debug('[fetchActivityCountByDate] 开始查询每天的活动总数')

    const response = await pyInvoke<{
      success: boolean
      data?: {
        dateCountMap: Record<string, number>
        totalDates: number
        totalActivities: number
      }
    }>('get_activity_count_by_date', {})

    if (!response?.success || !response.data?.dateCountMap) {
      console.warn('[fetchActivityCountByDate] 查询失败或无有效数据')
      return {}
    }

    console.debug('[fetchActivityCountByDate] ✅ 查询成功', {
      totalDates: response.data.totalDates,
      totalActivities: response.data.totalActivities
    })

    return response.data.dateCountMap
  } catch (error) {
    console.error('[fetchActivityCountByDate] 查询失败:', error)
    return {}
  }
}

/**
 * 获取增量更新的活动数据（基于版本号）
 * 用于窗口在顶部时，接收到后端新活动事件后拉取最新的活动
 * @param version 当前客户端的版本号
 * @param limit 返回的活动数量限制
 */
export async function fetchActivitiesIncremental(version: number, limit: number = 15): Promise<TimelineDay[]> {
  try {
    console.debug('[fetchActivitiesIncremental] 开始获取增量更新', { version, limit })

    const response = await pyInvoke<{
      success: boolean
      data?: {
        activities: any[]
        count: number
        maxVersion: number
        clientVersion: number
      }
    }>('get_activities_incremental', { version, limit })

    if (!response?.success || !response.data?.activities) {
      console.warn('[fetchActivitiesIncremental] 查询失败或无新活动')
      return []
    }

    // 构建活动对象并按日期分组
    const activitiesByDate = new Map<string, any[]>()

    response.data.activities.forEach((activity) => {
      const d = new Date(activity.startTime)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${day}`

      if (!activitiesByDate.has(dateStr)) {
        activitiesByDate.set(dateStr, [])
      }

      activitiesByDate.get(dateStr)!.push({
        ...activity,
        isNew: true // 标记为新活动用于动画
      })
    })

    // 构建时间线数据
    const timelineData: TimelineDay[] = Array.from(activitiesByDate.entries())
      .sort(([dateA], [dateB]) => (dateA > dateB ? -1 : 1))
      .map(([date, activities]) => ({
        date,
        activities,
        isNew: true // 标记日期块为新的
      }))

    console.debug('[fetchActivitiesIncremental] ✅ 获取成功', {
      newActivities: response.data.count,
      maxVersion: response.data.maxVersion
    })

    return timelineData
  } catch (error) {
    console.error('[fetchActivitiesIncremental] 获取失败:', error)
    return []
  }
}
