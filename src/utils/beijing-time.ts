const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;

/**
 * 获取北京时间某天的起止范围（返回 UTC Date 对象）
 * @param daysOffset 0=今天, -1=昨天, 1=明天
 */
export function getBeijingDayRange(daysOffset: number = 0): {
  gte: Date;
  lt: Date;
} {
  const now = new Date();
  const beijingNow = new Date(now.getTime() + BEIJING_OFFSET_MS);

  const target = new Date(beijingNow);
  target.setDate(target.getDate() + daysOffset);

  const year = target.getFullYear();
  const month = target.getMonth();
  const day = target.getDate();

  const gte = new Date(Date.UTC(year, month, day) - BEIJING_OFFSET_MS);
  const lt = new Date(gte.getTime() + 24 * 60 * 60 * 1000);

  return { gte, lt };
}
