import { getBeijingDayRange } from '../src/utils/beijing-time';

function test() {
  console.log('=== 北京时间工具函数测试 ===\n');

  const now = new Date();
  console.log(`当前 UTC 时间: ${now.toISOString()}`);

  // 测试默认参数（今天）
  const today = getBeijingDayRange();
  console.log('\n--- 今天 ---');
  console.log(`gte (UTC): ${today.gte.toISOString()}`);
  console.log(`lt  (UTC): ${today.lt.toISOString()}`);
  console.log(`间隔: ${(today.lt.getTime() - today.gte.getTime()) / (1000 * 60 * 60)} 小时`);

  // 测试昨天
  const yesterday = getBeijingDayRange(-1);
  console.log('\n--- 昨天 ---');
  console.log(`gte (UTC): ${yesterday.gte.toISOString()}`);
  console.log(`lt  (UTC): ${yesterday.lt.toISOString()}`);

  // 测试明天
  const tomorrow = getBeijingDayRange(1);
  console.log('\n--- 明天 ---');
  console.log(`gte (UTC): ${tomorrow.gte.toISOString()}`);
  console.log(`lt  (UTC): ${tomorrow.lt.toISOString()}`);

  // 简单断言验证
  const DAY_MS = 24 * 60 * 60 * 1000;
  const ok =
    today.lt.getTime() - today.gte.getTime() === DAY_MS &&
    yesterday.lt.getTime() - yesterday.gte.getTime() === DAY_MS &&
    tomorrow.lt.getTime() - tomorrow.gte.getTime() === DAY_MS;

  if (ok) {
    console.log('\n✅ 测试通过');
  } else {
    console.log('\n❌ 测试失败');
    process.exit(1);
  }
}

void test();
