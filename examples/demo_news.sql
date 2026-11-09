-- Optional fictional news for local testing. Run after both schema migrations.
INSERT IGNORE INTO news_category (name, sort_order) VALUES ('新能源演示', 100);

INSERT INTO news (title, description, content, author, category_id, publish_time)
SELECT '【虚构演示】新能源样车甲完成动力电池测试', '用于测试收藏总结和新闻时间线的虚构报道',
       '新能源样车甲搭载 58 千瓦时电池。本文为程序联调样例，车型和数据均为虚构。',
       '演示资料', category.id, '2026-01-05 09:00:00'
FROM news_category AS category
WHERE category.name = '新能源演示' AND NOT EXISTS (
    SELECT 1 FROM news WHERE title = '【虚构演示】新能源样车甲完成动力电池测试' AND category_id = category.id
);

INSERT INTO news (title, description, content, author, category_id, publish_time)
SELECT '【虚构演示】新能源样车乙发布快充方案', '用于测试收藏总结和新闻时间线的虚构报道',
       '新能源样车乙搭载 72 千瓦时电池，样例峰值快充功率为 180 千瓦。车型和数据均为虚构。',
       '演示资料', category.id, '2026-01-07 09:00:00'
FROM news_category AS category
WHERE category.name = '新能源演示' AND NOT EXISTS (
    SELECT 1 FROM news WHERE title = '【虚构演示】新能源样车乙发布快充方案' AND category_id = category.id
);
