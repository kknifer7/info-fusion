import OpenAI from 'openai';

const newsData = `2026年5月28日 星期四 农历四月十二
1.市监总局：自5月至12月部署整治"内卷式"竞争，聚焦直播带货、外卖等。
2.教育部留学服务中心特别提醒：从未将跨境远程文凭证书纳入认证范围。
3.疲劳驾驶认定新规明确适用范围：网约车、出租车不纳入8小时限驾规定。
4.神舟二十一号航天员乘组将于近日乘神舟二十二号载人飞船返回地球。
5.广州公积金新规：提高贷款额度上限，不超过购房总价款的80%。
6.湖南对自然灾害转移避险"吹哨人"给予奖励，最高奖5万元。
7.山西沁水开展煤矿违法行为有奖举报，最高奖200万元。
8.香港加码内地投资者投资账户监管，开户核查倒查至2023年1月。
9.小红书拿下2026年美加墨世界杯转播权，成为除央视、咪咕外唯一持权方。
10.升破6.78关口，人民币对美元汇率创2023年2月中旬以来新高。
11.柬埔寨等国电诈人员转至印尼作案，我使馆提醒在印尼中国公民注意防范。
12.NASA宣布永久月球基地计划：年内完成3项无人登月，2028年载人登月。
13.哈马斯确认其新任军事领导人在以军26日对巴勒斯坦加沙地带的袭击中身亡。
14.白宫：美伊谈判"进展顺利"。特朗普称伊朗即使放弃高浓缩铀也无法获得解除制裁。
15.伊朗官员：根据美伊初步协议草案，美将在所有战线全面停火60天。`;

const systemPrompt = `你是一位资深新闻编辑，擅长分析新闻性质并进行分类整理。

任务要求：
1. 分析每条新闻的性质，将其归类为【国内热点】或【国际热点】
2. 不要修改新闻原文内容，只进行分类整理
3. 严格按照下面的输出格式，不要添加任何其他内容
4. 【国内热点】和【国际热点】的序号均从1开始递增

输出格式（必须严格遵循）：
--- 开始 ---
【国内热点】
       1.xxxxx
       2.xxxxx
       3.xxxxx
       ...

【国际热点】
       1.xxxxx
       2.xxxxx
       3.xxxxx
       ...
--- 结束 ---`;

async function testDeepSeek() {
  const client = new OpenAI({
    apiKey: process.env['DEEPSEEK_API_KEY'],
    baseURL: 'https://api.deepseek.com',
  });

  try {
    const response = await client.chat.completions.create({
      model: 'deepseek-v4-flash',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: newsData },
      ],
    });

    console.log('✅ DeepSeek 分析完成\n');
    console.log(response.choices[0]?.message?.content);
  } catch (error) {
    console.error('❌ DeepSeek 调用失败:', error);
    process.exit(1);
  }
}

void testDeepSeek();
