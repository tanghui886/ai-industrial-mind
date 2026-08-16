-- 各工厂物料 mock 数据（SQLite / MySQL 通用）
-- 说明：路由上 code 具备唯一约束，使用 INSERT OR REPLACE 保证幂等（重复执行会覆盖同编码记录）
-- 字段顺序：code, name, category, factory, unit, stock_note, in_stock_units,
--           order_deducted_units, gap_units, support_units, in_transit_units,
--           purchase_units, arrival_date, status

-- 青岛 DFQD
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('STEEL', '耐候钢SPA-H', '钢板', 'DFQD', '吨', '当前库存2600吨', 2600, 1800, 0, 800, 600, 1200, '2026-09-05', '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('PAINT', '环氧防腐涂料', '油漆', 'DFQD', '吨', '底漆+面漆库存', 6500, 4500, 0, 2000, 0, 1500, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('CORNER', '角件/锁具', '角件', 'DFQD', '箱', '库存约600箱当量', 1500, 900, 320, 600, 400, 800, '2026-08-30', '需补货');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('FLOOR', '木地板', '地板', 'DFQD', '张', '进口硬木库存', 5200, 3700, 0, 1500, 0, 600, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('LOCK', '锁杆/铰链', '五金', 'DFQD', '套', '常规安全库存', 4200, 3000, 0, 1200, 0, 400, NULL, '充足');

-- 上海 DFSH
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('STEEL-SH', '耐候钢SPA-H', '钢板', 'DFSH', '吨', '在库1900吨', 1900, 1400, 0, 620, 450, 900, '2026-09-08', '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('PAINT-SH', '环氧防腐涂料', '油漆', 'DFSH', '吨', '底漆+面漆库存', 4800, 3300, 0, 1600, 0, 1200, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('CORNER-SH', '角件/锁具', '角件', 'DFSH', '箱', '库存约450箱当量', 1100, 700, 320, 480, 300, 600, '2026-09-01', '需补货');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('FLOOR-SH', '木地板', '地板', 'DFSH', '张', '进口硬木库存', 3900, 2800, 0, 1100, 0, 500, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('LOCK-SH', '锁杆/铰链', '五金', 'DFSH', '套', '常规安全库存', 3100, 2200, 0, 900, 0, 300, NULL, '充足');

-- 南通 DFNT
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('STEEL-NT', '耐候钢SPA-H', '钢板', 'DFNT', '吨', '在库2100吨', 2100, 1600, 0, 700, 500, 1000, '2026-09-06', '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('PAINT-NT', '环氧防腐涂料', '油漆', 'DFNT', '吨', '底漆+面漆库存', 5400, 3800, 0, 1800, 0, 1100, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('CORNER-NT', '角件/锁具', '角件', 'DFNT', '箱', '库存约520箱当量', 1300, 850, 320, 560, 350, 700, '2026-08-31', '需补货');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('FLOOR-NT', '木地板', '地板', 'DFNT', '张', '进口硬木库存', 4600, 3400, 0, 1300, 0, 550, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('LOCK-NT', '锁杆/铰链', '五金', 'DFNT', '套', '常规安全库存', 3600, 2600, 0, 950, 0, 350, NULL, '充足');

-- 连云港 DFLYG
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('STEEL-LYG', '耐候钢SPA-H', '钢板', 'DFLYG', '吨', '在库1700吨', 1700, 1200, 0, 560, 400, 800, '2026-09-09', '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('PAINT-LYG', '环氧防腐涂料', '油漆', 'DFLYG', '吨', '底漆+面漆库存', 4300, 3000, 0, 1400, 0, 1000, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('CORNER-LYG', '角件/锁具', '角件', 'DFLYG', '箱', '库存约400箱当量', 1000, 650, 320, 430, 280, 550, '2026-09-02', '需补货');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('FLOOR-LYG', '木地板', '地板', 'DFLYG', '张', '进口硬木库存', 3500, 2500, 0, 1000, 0, 450, NULL, '充足');
INSERT INTO material (code, name, category, factory, unit, stock_note, in_stock_units, order_deducted_units, gap_units, support_units, in_transit_units, purchase_units, arrival_date, status) VALUES ('LOCK-LYG', '锁杆/铰链', '五金', 'DFLYG', '套', '常规安全库存', 2800, 2000, 0, 800, 0, 300, NULL, '充足');